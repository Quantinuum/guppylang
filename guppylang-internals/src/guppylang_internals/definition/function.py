import ast
import inspect
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import hugr.build.function as hf
import hugr.tys as ht
from hugr import Node, Wire
from hugr.build.dfg import DefinitionBuilder, OpVar
from hugr.hugr.node_port import ToNode

from guppylang_internals.ast_util import AstNode, annotate_location, with_loc, with_type
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
    PartiallyMonomorphizedArgs,
)
from guppylang_internals.compiler.func_compiler import compile_global_func_def
from guppylang_internals.definition.common import (
    CheckableDef,
    MonomorphizableDef,
    MonomorphizedDef,
    ParsableDef,
    UnknownSourceError,
)
from guppylang_internals.definition.metadata import GuppyMetadata, add_metadata
from guppylang_internals.definition.value import (
    CallableDef,
    CallReturnWires,
    CompiledCallableDef,
    CompiledHugrNodeDef,
)
from guppylang_internals.error import GuppyError
from guppylang_internals.nodes import GlobalCall
from guppylang_internals.span import SourceMap
from guppylang_internals.tys.subst import Inst, Subst
from guppylang_internals.tys.ty import FunctionType, Type, UnitaryFlags, type_to_row

if TYPE_CHECKING:
    from guppylang_internals.tys.param import Parameter

PyFunc = Callable[..., Any]


@dataclass(frozen=True)
class RawFunctionDef(ParsableDef):
    """A raw function definition provided by the user.

    The raw definition stores exactly what the user has written (i.e. the AST), without
    any additional checking or parsing. Furthermore, we store the values of the Python
    variables in scope at the point of definition.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was defined.
        python_func: The Python function to be defined.
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
        return ParsedFunctionDef(
            self.id,
            self.name,
            func_ast,
            ty,
            docstring,
            metadata=self.metadata,
        )


@dataclass(frozen=True)
class ParsedFunctionDef(CheckableDef, CallableDef):
    """A function definition with parsed and checked signature.

    In particular, this means that we have determined a type for the function and are
    ready to check the function body.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was defined.
        ty: The type of the function.
        python_scope: The Python scope where the function was defined.
        docstring: The docstring of the function.
    """

    defined_at: ast.FunctionDef
    ty: FunctionType
    docstring: str | None

    description: str = field(default="function", init=False)

    metadata: GuppyMetadata | None = field(default=None, kw_only=True)

    def check(self, globals: Globals) -> "CheckedFunctionDef":
        """Type checks the body of the function."""
        # Add python variable scope to the globals
        cfg = check_global_func_def(self.defined_at, self.ty, globals)
        return CheckedFunctionDef(
            self.id,
            self.name,
            self.defined_at,
            self.ty,
            self.docstring,
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
        return node, subst

    def synthesize_call(
        self, args: list[ast.expr], node: AstNode, ctx: Context
    ) -> tuple[ast.expr, Type]:
        """Synthesizes the return type of a function call."""
        # Use default implementation from the expression checker
        args, ty, inst = synthesize_call(self.ty, args, node, ctx)
        node = with_loc(node, GlobalCall(def_id=self.id, args=args, type_args=inst))
        return with_type(ty, node), ty


@dataclass(frozen=True)
class CheckedFunctionDef(ParsedFunctionDef, MonomorphizableDef):
    """Type checked version of a user-defined function that is ready to be compiled.

    In particular, this means that we have a constructed and type checked a control-flow
    graph for the function body.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was defined.
        ty: The type of the function.
        python_scope: The Python scope where the function was defined.
        docstring: The docstring of the function.
        cfg: The type- and linearity-checked CFG for the function body.
    """

    cfg: CheckedCFG[Place]

    @property
    def params(self) -> "Sequence[Parameter]":
        """Generic parameters of this function."""
        return self.ty.params

    def monomorphize(
        self,
        module: DefinitionBuilder[OpVar],
        mono_args: "PartiallyMonomorphizedArgs",
        ctx: "CompilerContext",
    ) -> "CompiledFunctionDef":
        """Adds a Hugr `FuncDefn` node for the (partially) monomorphized function to the
        Hugr.

        Note that we don't compile the function body at this point since we don't have
        access to the other compiled functions yet. The body is compiled later in
        `CompiledFunctionDef.compile_inner()`.
        """
        mono_ty = self.ty.instantiate_partial(mono_args)
        hugr_ty = mono_ty.to_hugr_poly(ctx)
        func_def = module.module_root_builder().define_function(
            self.name, hugr_ty.body.input, hugr_ty.body.output, hugr_ty.params
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
            mono_args,
            mono_ty,
            self.docstring,
            self.cfg,
            func_def,
            metadata=self.metadata,
        )


@dataclass(frozen=True)
class CompiledFunctionDef(
    CheckedFunctionDef, CompiledCallableDef, MonomorphizedDef, CompiledHugrNodeDef
):
    """A function definition with a corresponding Hugr node.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was defined.
        mono_args: Partial monomorphization of the generic type parameters.
        ty: The type of the function after partial monomorphization.
        python_scope: The Python scope where the function was defined.
        docstring: The docstring of the function.
        cfg: The type- and linearity-checked CFG for the function body.
        func_def: The Hugr function definition.
    """

    func_def: hf.Function

    @property
    def hugr_node(self) -> Node:
        """The Hugr node this definition was compiled into."""
        return self.func_def.parent_node

    def load_with_args(
        self,
        type_args: Inst,
        dfg: DFContainer,
        ctx: CompilerContext,
        node: AstNode,
    ) -> Wire:
        """Loads the function as a value into a local Hugr dataflow graph."""
        return load_with_args(type_args, dfg, self.ty, self.func_def)

    def compile_call(
        self,
        args: list[Wire],
        type_args: Inst,
        dfg: DFContainer,
        ctx: CompilerContext,
        node: AstNode,
    ) -> CallReturnWires:
        """Compiles a call to the function."""
        return compile_call(args, type_args, dfg, self.ty, self.func_def)

    def compile_inner(self, globals: CompilerContext) -> None:
        """Compiles the body of the function."""
        compile_global_func_def(self, self.func_def, globals)


def load_with_args(
    type_args: Inst,
    dfg: DFContainer,
    ty: FunctionType,
    func: ToNode,
) -> Wire:
    """Loads the function as a value into a local Hugr dataflow graph."""
    func_ty: ht.FunctionType = ty.instantiate(type_args).to_hugr(dfg.ctx)
    type_args = [ta.to_hugr(dfg.ctx) for ta in type_args]
    return dfg.builder.load_function(func, func_ty, type_args)


def compile_call(
    args: list[Wire],
    type_args: Inst,  # Non-monomorphized type args only
    dfg: DFContainer,
    ty: FunctionType,
    func: ToNode,
) -> CallReturnWires:
    """Compiles a call to the function."""
    func_ty: ht.FunctionType = ty.instantiate(type_args).to_hugr(dfg.ctx)
    type_args = [arg.to_hugr(dfg.ctx) for arg in type_args]
    num_returns = len(type_to_row(ty.output))
    call = dfg.builder.call(func, *args, instantiation=func_ty, type_args=type_args)
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


def parse_source(source_lines: list[str], line_offset: int) -> tuple[str, ast.AST, int]:
    """Parses a list of source lines into an AST object.

    Also takes care of correctly parsing source that is indented.

    Returns the full source, the parsed AST node, and a potentially updated line number
    offset.
    """
    source = "".join(source_lines)  # Lines already have trailing \n's
    if source_lines[0][0].isspace():
        # This means the function is indented, so we cannot parse it straight away.
        # Running `textwrap.dedent` would mess up the column number in spans. Instead,
        # we'll just wrap the source into a dummy class definition so the indent becomes
        # valid
        cls_node = ast.parse("class _:\n" + source).body[0]
        assert isinstance(cls_node, ast.ClassDef)
        node = cls_node.body[0]
        line_offset -= 1
    else:
        node = ast.parse(source).body[0]
    return source, node, line_offset
