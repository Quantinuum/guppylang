import ast
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from hugr import Node, Wire
from hugr.build import function as hf
from hugr.build.dfg import DefinitionBuilder, OpVar
from hugr.metadata import HugrDebugInfo

from guppylang_internals.ast_util import (
    AstNode,
    has_empty_body,
    with_loc,
    with_type,
)
from guppylang_internals.checker.core import Context, Globals
from guppylang_internals.checker.expr_checker import check_call, synthesize_call
from guppylang_internals.checker.func_checker import check_signature
from guppylang_internals.compiler.core import CompilerContext, DFContainer
from guppylang_internals.debug_mode import debug_mode_enabled
from guppylang_internals.definition.common import (
    CheckableGenericDef,
    CompilableDef,
    ParsableDef,
    UserProvidedLinkName,
)
from guppylang_internals.definition.function import (
    PyFunc,
    compile_call,
    default_func_link_name,
    load,
    make_subprogram_record,
    monomorphized_link_name,
    parse_py_func,
)
from guppylang_internals.definition.value import (
    CallableDef,
    CallReturnWires,
    CompiledCallableDef,
    CompiledHugrNodeDef,
)
from guppylang_internals.diagnostic import Error
from guppylang_internals.engine import ENGINE
from guppylang_internals.error import GuppyError
from guppylang_internals.metadata.common import FunctionMetadata, add_metadata
from guppylang_internals.nodes import GlobalCall
from guppylang_internals.span import SourceMap
from guppylang_internals.tys.param import Parameter
from guppylang_internals.tys.subst import Inst, Subst
from guppylang_internals.tys.ty import Type, UnitaryFlags


@dataclass(frozen=True)
class BodyNotEmptyError(Error):
    title: ClassVar[str] = "Unexpected function body"
    span_label: ClassVar[str] = "Body of declared function `{name}` must be empty"
    name: str


@dataclass(frozen=True)
class MonomorphizeError(Error):
    title: ClassVar[str] = "Invalid function declaration"
    span_label: ClassVar[str] = (
        "Function declaration `{name}` is not allowed to be generic over `{param}`"
    )
    name: str
    param: Parameter


@dataclass(frozen=True)
class RawFunctionDecl(ParsableDef, UserProvidedLinkName):
    """A raw function declaration provided by the user.

    The raw declaration stores exactly what the user has written (i.e. the AST), without
    any additional checking or parsing.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was defined.
        python_func: The Python function object corresponding to the declaration.
        link_name: The external name for this declaration, applied to the Hugr node and
            other representations
    """

    python_func: PyFunc

    description: str = field(default="function", init=False)

    unitary_flags: UnitaryFlags = field(default=UnitaryFlags.NoFlags, kw_only=True)

    metadata: FunctionMetadata | None = field(default=None, kw_only=True)

    def parse(self, globals: Globals, sources: SourceMap) -> "ParsedFunctionDecl":
        """Parses and checks the user-provided signature of the function."""
        func_ast, docstring = parse_py_func(self.python_func, sources)
        ty = check_signature(
            func_ast, globals, self.id, unitary_flags=self.unitary_flags
        )
        link_name = self._user_set_link_name or default_func_link_name(self)

        # TODO: For the guppylang 1.0 break, we should consider disallowing generic
        #  declarations. For now though, we must allow them to avoid breakage...

        if not has_empty_body(func_ast):
            raise GuppyError(BodyNotEmptyError(func_ast.body[0], self.name))
        return ParsedFunctionDecl(
            id=self.id,
            name=self.name,
            defined_at=func_ast,
            ty=ty,
            docstring=docstring,
            link_name=link_name,
            metadata=self.metadata,
        )


@dataclass(frozen=True)
class ParsedFunctionDecl(CheckableGenericDef, CallableDef):
    """A function declaration with parsed and checked signature.

    In particular, this means that we have determined a type for the function.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was declared.
        ty: The type of the function.
        docstring: The docstring of the function.
        link_name: The external name for this declaration, applied to the Hugr node and
            other representations
    """

    defined_at: ast.FunctionDef
    docstring: str | None
    link_name: str
    metadata: FunctionMetadata | None = field(default=None, kw_only=True)

    @property
    def params(self) -> Sequence[Parameter]:
        return self.ty.params

    def check(self, type_args: Inst, globals: Globals) -> "CheckedFunctionDecl":
        mono_ty = self.ty.instantiate_partial(type_args)
        mono_link_name = monomorphized_link_name(self.link_name, type_args)
        return CheckedFunctionDecl(
            id=self.id,
            name=self.name,
            defined_at=self.defined_at,
            ty=mono_ty,
            docstring=self.docstring,
            link_name=mono_link_name,
            type_args=type_args,
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
    ) -> tuple[GlobalCall, Type]:
        """Synthesizes the return type of a function call."""
        # Use default implementation from the expression checker
        args, ty, inst = synthesize_call(self.ty, args, node, ctx)
        node = with_loc(node, GlobalCall(def_id=self.id, args=args, type_args=inst))
        ENGINE.register_generic_use(self, inst)
        return with_type(ty, node), ty


@dataclass(frozen=True)
class CheckedFunctionDecl(ParsedFunctionDecl, CompilableDef):
    """A checked, monomorphized version of a function declaration.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was declared.
        ty: The monomorphic type of the function.
        docstring: The docstring of the function.
        link_name: The external name for this declaration, applied to the Hugr node and
            other representations
    """

    type_args: Inst

    def compile_outer(
        self, module: DefinitionBuilder[OpVar], ctx: CompilerContext
    ) -> "CompiledFunctionDecl":
        """Adds a Hugr `FuncDecl` node for this function to the Hugr."""
        assert isinstance(module, hf.Module), (
            "Functions can only be declared in modules"
        )
        module: hf.Module = module

        node = module.declare_function(self.link_name, self.ty.to_hugr_poly(ctx))
        add_metadata(
            node,
            self.metadata,
            additional_metadata={"unitary": self.ty.unitary_flags.value},
        )
        if debug_mode_enabled():
            node.metadata[HugrDebugInfo] = make_subprogram_record(
                self.defined_at, ctx, is_decl=True
            )
        return CompiledFunctionDecl(
            id=self.id,
            name=self.name,
            defined_at=self.defined_at,
            ty=self.ty,
            docstring=self.docstring,
            link_name=self.link_name,
            type_args=self.type_args,
            declaration=node,
            metadata=self.metadata,
        )


@dataclass(frozen=True)
class CompiledFunctionDecl(
    CheckedFunctionDecl, CompiledCallableDef, CompiledHugrNodeDef
):
    """A function declaration with a corresponding Hugr node.

    Args:
        id: The unique definition identifier.
        name: The name of the function.
        defined_at: The AST node where the function was declared.
        ty: The type of the function.
        docstring: The docstring of the function.
        link_name: The external name for this declaration, applied to the Hugr node and
            other representations
        declaration: The Hugr node corresponding to this function declaration.
    """

    declaration: Node

    @property
    def hugr_node(self) -> Node:
        """The Hugr node this definition was compiled into."""
        return self.declaration

    def load(self, dfg: DFContainer, ctx: CompilerContext, node: AstNode) -> Wire:
        """Loads the function as a value into a local Hugr dataflow graph."""
        # Use implementation from function definition.
        return load(dfg, self.declaration)

    def compile_call(
        self,
        args: list[Wire],
        dfg: DFContainer,
        ctx: CompilerContext,
        node: AstNode,
    ) -> CallReturnWires:
        """Compiles a call to the function."""
        # Use implementation from function definition.
        return compile_call(args, dfg, self.ty, self.declaration, node)
