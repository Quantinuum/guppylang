import ast
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import hugr.build.function as hf
import hugr.tys as ht
from hugr import Node, Wire
from hugr.build.dfg import DefinitionBuilder, OpVar

from guppylang_internals.ast_util import AstNode, with_loc
from guppylang_internals.checker.core import Context, Globals
from guppylang_internals.checker.errors.generic import UnsupportedError
from guppylang_internals.checker.expr_checker import (
    check_call,
    synthesize_call,
)
from guppylang_internals.checker.func_checker import (
    check_signature,
)
from guppylang_internals.compiler.core import CompilerContext, DFContainer
from guppylang_internals.definition.common import (
    CompilableDef,
    ParsableDef,
)
from guppylang_internals.definition.function import parse_py_func
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
from guppylang_internals.tys.ty import FunctionType, Type, type_to_row

PyFunc = Callable[..., Any]


@dataclass(frozen=True)
class RawTracedFunctionDef(ParsableDef):
    python_func: PyFunc

    description: str = field(default="function", init=False)

    def parse(self, globals: Globals, sources: SourceMap) -> "TracedFunctionDef":
        """Parses and checks the user-provided signature of the function."""
        func_ast, _docstring = parse_py_func(self.python_func, sources)
        ty = check_signature(func_ast, globals, self.id)
        if ty.parametrized:
            raise GuppyError(UnsupportedError(func_ast, "Generic comptime functions"))
        return TracedFunctionDef(self.id, self.name, func_ast, ty, self.python_func)


@dataclass(frozen=True)
class TracedFunctionDef(RawTracedFunctionDef, CallableDef, CompilableDef):
    python_func: PyFunc
    ty: FunctionType
    defined_at: ast.FunctionDef

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
        return node, ty

    def compile_outer(
        self, module: DefinitionBuilder[OpVar], ctx: CompilerContext
    ) -> "CompiledTracedFunctionDef":
        """Adds a Hugr `FuncDefn` node for this function to the Hugr.

        Note that we don't compile the function body at this point since we don't have
        access to the other compiled functions yet. The body is compiled later in
        `CompiledFunctionDef.compile_inner()`.
        """
        func_type = self.ty.to_hugr_poly(ctx)
        func_def = module.module_root_builder().define_function(
            self.name, func_type.body.input, func_type.body.output, func_type.params
        )
        return CompiledTracedFunctionDef(
            self.id,
            self.name,
            self.defined_at,
            self.ty,
            self.python_func,
            func_def,
        )


@dataclass(frozen=True)
class CompiledTracedFunctionDef(
    TracedFunctionDef, CompiledCallableDef, CompiledHugrNodeDef
):
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
        func_ty: ht.FunctionType = self.ty.instantiate(type_args).to_hugr(ctx)
        type_args: list[ht.TypeArg] = [arg.to_hugr(ctx) for arg in type_args]
        return dfg.builder.load_function(self.func_def, func_ty, type_args)

    def compile_call(
        self,
        args: list[Wire],
        type_args: Inst,
        dfg: DFContainer,
        ctx: CompilerContext,
        node: AstNode,
    ) -> CallReturnWires:
        """Compiles a call to the function."""
        func_ty: ht.FunctionType = self.ty.instantiate(type_args).to_hugr(ctx)
        type_args: list[ht.TypeArg] = [arg.to_hugr(ctx) for arg in type_args]
        num_returns = len(type_to_row(self.ty.output))
        call = dfg.builder.call(
            self.func_def, *args, instantiation=func_ty, type_args=type_args
        )
        return CallReturnWires(
            regular_returns=list(call[:num_returns]),
            inout_returns=list(call[num_returns:]),
        )

    def compile_inner(self, ctx: CompilerContext) -> None:
        """Compiles the body of the function by tracing it."""
        from guppylang_internals.tracing.function import trace_function

        trace_function(self.python_func, self.ty, self.func_def, ctx, self.defined_at)
