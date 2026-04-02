import ast
import inspect
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import hugr.build.function as hf
from hugr import Node, Wire
from hugr.build.dfg import DefinitionBuilder, OpVar
from hugr.hugr.node_port import ToNode

from guppylang_internals.ast_util import (
    AstNode,
    annotate_location,
    parse_source,
    with_loc,
    with_type,
)
from guppylang_internals.checker.cfg_checker import CheckedCFG
from guppylang_internals.checker.core import Context, Globals, Place
from guppylang_internals.checker.errors.generic import ExpectedError
from guppylang_internals.checker.expr_checker import check_call, synthesize_call
from guppylang_internals.checker.func_checker import (
    check_global_func_def,
    check_signature,
    parse_function_with_docstring,
)
from guppylang_internals.compiler.core import (
    CompilerContext,
    DFContainer,
)
from guppylang_internals.compiler.func_compiler import compile_global_func_def
from guppylang_internals.definition.common import (
    CheckableGenericDef,
    CompilableDef,
    ParsableDef,
    UnknownSourceError,
    UserProvidedLinkName,
)
from guppylang_internals.definition.enum import ParsedEnumDef
from guppylang_internals.definition.metadata import GuppyMetadata, add_metadata
from guppylang_internals.definition.struct import ParsedStructDef
from guppylang_internals.definition.value import (
    CallableDef,
    CallReturnWires,
    CompiledCallableDef,
    CompiledHugrNodeDef,
)
from guppylang_internals.engine import DEF_STORE, ENGINE
from guppylang_internals.error import GuppyError
from guppylang_internals.nodes import GlobalCall
from guppylang_internals.span import SourceMap
from guppylang_internals.tys.arg import ConstArg, TypeArg
from guppylang_internals.tys.const import ConstValue
from guppylang_internals.tys.subst import Inst, Subst
from guppylang_internals.tys.ty import FunctionType, Type, UnitaryFlags, type_to_row

if TYPE_CHECKING:
    from guppylang_internals.definition.declaration import RawFunctionDecl
    from guppylang_internals.tys.param import Parameter

PyFunc = Callable[..., Any]


def default_func_link_name(raw_def: "RawFunctionDef | RawFunctionDecl") -> str:
    if (parent_ty_id := DEF_STORE.type_member_parents.get(raw_def.id)) is not None:
        parent = ENGINE.get_parsed(parent_ty_id)
        if isinstance(parent, (ParsedStructDef, ParsedEnumDef)):
            return f"{parent.link_name_prefix}.{raw_def.python_func.__name__}"

    return f"{raw_def.python_func.__module__}.{raw_def.python_func.__qualname__}"


def monomorphized_link_name(link_name: str, mono_args: Inst) -> str:
    """Returns a unique link name for the monomorphized version of a function.

    If the function is not generic, then the original link name is preserved.
    """
    if not mono_args:
        return link_name
    arg_strings = []
    for arg in mono_args:
        match arg:
            case TypeArg(ty=ty):
                arg_strings.append(str(ty))
            case ConstArg(const=ConstValue(value=v)):
                arg_strings.append(str(v))
    return f"{link_name}$" + "&".join(arg_strings)


@dataclass(frozen=True)
class RawFunctionDef(ParsableDef, UserProvidedLinkName):
    """A raw function definition provided by the user.

    The raw definition stores exactly what the user has written (i.e. the AST), without
    any additional checking or parsing. Furthermore, we store the values of the Python
    variables in scope at the point of definition.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was defined.
        python_func: The Python function to be defined.
        link_name: The external name for this function (applied to the Hugr node, and
            other representations, regardless of whether the function is actually
            visible for linking)
    """

    python_func: PyFunc

    description: str = field(default="function", init=False)

    unitary_flags: UnitaryFlags = field(default=UnitaryFlags.NoFlags, kw_only=True)

    metadata: GuppyMetadata | None = field(default=None, kw_only=True)

    def parse(self, globals: Globals, sources: SourceMap) -> "ParsedFunctionDef":
        """Parses and checks the user-provided signature of the function."""
        func_ast, docstring = parse_py_func(self.python_func, sources)
        ty = check_signature(
            func_ast, globals, self.id, unitary_flags=self.unitary_flags
        )
        link_name = self._user_set_link_name or default_func_link_name(self)

        return ParsedFunctionDef(
            self.id,
            self.name,
            func_ast,
            ty,
            docstring,
            link_name,
            metadata=self.metadata,
        )


@dataclass(frozen=True)
class ParsedFunctionDef(CheckableGenericDef, CallableDef):
    """A function definition with parsed and checked signature.

    In particular, this means that we have determined a type for the function and are
    ready to check the function body.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was defined.
        ty: The type of the function.
        docstring: The docstring of the function.
        link_name: The external name for this function (applied to the Hugr node, and
            other representations, regardless of whether the function is actually
            visible for linking)
    """

    defined_at: ast.FunctionDef
    ty: FunctionType
    docstring: str | None
    link_name: str

    description: str = field(default="function", init=False)

    metadata: GuppyMetadata | None = field(default=None, kw_only=True)

    @property
    def params(self) -> "Sequence[Parameter]":
        """Generic parameters of this function."""
        return self.ty.params

    def check(self, type_args: Inst, globals: Globals) -> "CheckedFunctionDef":
        """Type checks the body of the function."""
        cfg = check_global_func_def(self.defined_at, self.ty, type_args, globals)
        mono_ty = self.ty.instantiate_partial(type_args)
        mono_link_name = monomorphized_link_name(self.link_name, type_args)
        return CheckedFunctionDef(
            self.id,
            self.name,
            self.defined_at,
            mono_ty,
            self.docstring,
            mono_link_name,
            cfg,
            metadata=self.metadata,
        )

    def check_call(
        self, args: list[ast.expr], ty: Type, node: AstNode, ctx: Context
    ) -> tuple[ast.expr, Subst]:
        """Checks the return type of a function call against a given type."""
        # Use default implementation from the expression checker
        args, subst, inst = check_call(self.ty, args, ty, node, ctx)
        node = with_loc(node, GlobalCall(def_id=self.id, args=args, type_args=inst))
        ENGINE.register_generic_use(self, inst)
        return node, subst

    def synthesize_call(
        self, args: list[ast.expr], node: AstNode, ctx: Context
    ) -> tuple[ast.expr, Type]:
        """Synthesizes the return type of a function call."""
        # Use default implementation from the expression checker
        args, ty, inst = synthesize_call(self.ty, args, node, ctx)
        node = with_loc(node, GlobalCall(def_id=self.id, args=args, type_args=inst))
        ENGINE.register_generic_use(self, inst)
        return with_type(ty, node), ty


@dataclass(frozen=True)
class CheckedFunctionDef(ParsedFunctionDef, CompilableDef):
    """Type checked version of a user-defined function that is ready to be compiled.

    In particular, this means that we have a constructed and type checked a control-flow
    graph for the function body.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was defined.
        ty: The type of the function.
        docstring: The docstring of the function.
        link_name: The external name for this function (applied to the Hugr node, and
            other representations, regardless of whether the function is actually
            visible for linking)
        cfg: The type- and linearity-checked CFG for the function body.
    """

    cfg: CheckedCFG[Place]

    def __post_init__(self) -> None:
        # We should be monomorphized at this point
        assert not self.params

    def compile_outer(
        self,
        module: DefinitionBuilder[OpVar],
        ctx: "CompilerContext",
    ) -> "CompiledFunctionDef":
        """Adds a Hugr `FuncDefn` node for the monomorphized function to the Hugr.

        Note that we don't compile the function body at this point since we don't have
        nodes for the other compiled functions yet. The body is compiled later in
        `CompiledFunctionDef.compile_inner()`.
        """
        hugr_ty = self.ty.to_hugr_poly(ctx)
        func_def = module.module_root_builder().define_function(
            self.link_name,
            hugr_ty.body.input,
            hugr_ty.body.output,
            hugr_ty.params,
            visibility="Public" if self.id in ctx.exported_defs else "Private",
        )
        add_metadata(
            func_def,
            self.metadata,
            additional_metadata={"unitary": self.ty.unitary_flags.value},
        )
        return CompiledFunctionDef(
            self.id,
            self.name,
            self.defined_at,
            self.ty,
            self.docstring,
            self.link_name,
            self.cfg,
            func_def,
            metadata=self.metadata,
        )


@dataclass(frozen=True)
class CompiledFunctionDef(CheckedFunctionDef, CompiledCallableDef, CompiledHugrNodeDef):
    """A function definition with a corresponding Hugr node.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was defined.
        mono_args: Partial monomorphization of the generic type parameters.
        ty: The type of the function after partial monomorphization.
        docstring: The docstring of the function.
        link_name: The external name for this function (applied to the Hugr node, and
            other representations, regardless of whether the function is actually
            visible for linking)
        cfg: The type- and linearity-checked CFG for the function body.
        func_def: The Hugr function definition.
    """

    func_def: hf.Function

    @property
    def hugr_node(self) -> Node:
        """The Hugr node this definition was compiled into."""
        return self.func_def.parent_node

    def load(self, dfg: DFContainer, ctx: CompilerContext, node: AstNode) -> Wire:
        """Loads the function as a value into a local Hugr dataflow graph."""
        return load(dfg, self.func_def)

    def compile_call(
        self,
        args: list[Wire],
        dfg: DFContainer,
        ctx: CompilerContext,
        node: AstNode,
    ) -> CallReturnWires:
        """Compiles a call to the function."""
        return compile_call(args, dfg, self.ty, self.func_def)

    def compile_inner(self, globals: CompilerContext) -> None:
        """Compiles the body of the function."""
        compile_global_func_def(self, self.func_def, globals)


def load(dfg: DFContainer, func: ToNode) -> Wire:
    """Loads the function as a value into a local Hugr dataflow graph."""
    return dfg.builder.load_function(func)


def compile_call(
    args: list[Wire],
    dfg: DFContainer,
    ty: FunctionType,
    func: ToNode,
) -> CallReturnWires:
    """Compiles a call to the function."""
    num_returns = len(type_to_row(ty.output))
    call = dfg.builder.call(func, *args)
    return CallReturnWires(
        regular_returns=list(call[:num_returns]),
        inout_returns=list(call[num_returns:]),
    )


def parse_py_func(f: PyFunc, sources: SourceMap) -> tuple[ast.FunctionDef, str | None]:
    source_lines, line_offset = inspect.getsourcelines(f)
    source, func_ast, line_offset = parse_source(source_lines, line_offset)
    file = inspect.getsourcefile(f)
    if file is None:
        raise GuppyError(UnknownSourceError(None, f))
    sources.add_file(file)
    annotate_location(func_ast, source, file, line_offset)
    if not isinstance(func_ast, ast.FunctionDef):
        raise GuppyError(ExpectedError(func_ast, "a function definition"))
    return parse_function_with_docstring(func_ast)
