import ast
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import hugr.build.function as hf
import hugr.tys as ht
from hugr import Node, Wire, val
from hugr.build.dfg import DefinitionBuilder, OpVar
from hugr.metadata import HugrDebugInfo
from typing_extensions import assert_never, override

from guppylang_internals.ast_util import AstNode, with_loc
from guppylang_internals.checker.core import Context, Globals
from guppylang_internals.checker.expr_checker import (
    check_call,
    synthesize_call,
)
from guppylang_internals.checker.func_checker import (
    check_signature,
)
from guppylang_internals.compiler.builder import FunctionBuilder
from guppylang_internals.compiler.core import CompilerContext, DFContainer
from guppylang_internals.debug_mode import debug_mode_enabled
from guppylang_internals.definition.common import (
    CheckableGenericDef,
    CompilableDef,
    ParsableDef,
)
from guppylang_internals.definition.function import (
    make_subprogram_record,
    parse_py_func,
)
from guppylang_internals.definition.value import (
    CallableDef,
    CallReturnWires,
    CompiledCallableDef,
    CompiledHugrNodeDef,
    CompiledValueDef,
)
from guppylang_internals.error import GuppyComptimeError
from guppylang_internals.metadata.common import FunctionMetadata, add_metadata
from guppylang_internals.nodes import GlobalCall
from guppylang_internals.span import SourceMap
from guppylang_internals.tracing.state import (
    TraceCall,
    TraceFunctionLoad,
    TraceLoad,
    TraceOperation,
    TraceWire,
)
from guppylang_internals.tys import Effect
from guppylang_internals.tys.arg import Argument
from guppylang_internals.tys.param import Parameter
from guppylang_internals.tys.subst import Inst, Subst
from guppylang_internals.tys.ty import InputFlags, Type, UnitaryFlags, type_to_row

PyFunc = Callable[..., Any]

if TYPE_CHECKING:
    from guppylang_internals.tracing.state import Trace


@dataclass(frozen=True)
class RawTracedFunctionDef(ParsableDef):
    python_func: PyFunc

    description: str = field(default="function", init=False)

    unitary_flags: UnitaryFlags = field(default=UnitaryFlags.NoFlags, kw_only=True)

    metadata: FunctionMetadata | None = field(default=None, kw_only=True)

    def parse(self, globals: Globals, sources: SourceMap) -> "TracedFunctionDef":
        """Parses and checks the user-provided signature of the function."""
        func_ast, _docstring = parse_py_func(self.python_func, sources)
        ty = check_signature(
            func_ast, globals, self.id, unitary_flags=self.unitary_flags
        )
        return TracedFunctionDef(
            self.id,
            self.name,
            func_ast,
            ty,
            self.python_func,
            unitary_flags=self.unitary_flags,
            metadata=self.metadata,
        )


@dataclass(frozen=True)
class TracedFunctionDef(RawTracedFunctionDef, CallableDef, CheckableGenericDef):
    defined_at: ast.FunctionDef

    @property
    def params(self) -> Sequence[Parameter]:
        """Generic parameters of this function."""
        return self.ty.params

    def check(self, type_args: Inst, globals: Globals) -> "TracedMonoFunctionDef":
        """Monomorphizes the function for the given type arg instantiation.

        Executes the Python body while recording a replayable HUGR trace.
        """
        mono_ty = self.ty.instantiate_partial(type_args)
        generic_args = {
            param.name: arg
            for param, arg in zip(self.ty.params, type_args, strict=True)
        }
        from guppylang_internals.tracing.function import trace_function

        trace = trace_function(
            self.python_func,
            mono_ty,
            sum(InputFlags.Comptime not in inp.flags for inp in mono_ty.inputs),
            generic_args,
            self.defined_at,
            self,
        )
        return TracedMonoFunctionDef(
            self.id,
            self.name,
            self.defined_at,
            mono_ty,
            self.python_func,
            generic_args,
            trace,
            unitary_flags=self.unitary_flags,
            metadata=self.metadata,
        )

    @override
    def check_call(
        self, args: list[ast.expr], ty: Type, node: ast.Call, ctx: Context
    ) -> tuple[ast.expr, Subst]:
        """Checks the return type of a function call against a given type."""
        # Use default implementation from the expression checker
        args, subst, inst = check_call(self.ty, args, ty, node, ctx)
        node = with_loc(node, GlobalCall(def_id=self.id, args=args, type_args=inst))
        return node, subst

    @override
    def synthesize_call(
        self, args: list[ast.expr], node: AstNode, ctx: Context
    ) -> tuple[ast.expr, Type]:
        """Synthesizes the return type of a function call."""
        # Use default implementation from the expression checker
        args, ty, inst = synthesize_call(self.ty, args, node, ctx)
        node = with_loc(node, GlobalCall(def_id=self.id, args=args, type_args=inst))
        return node, ty


@dataclass(frozen=True)
class TracedMonoFunctionDef(TracedFunctionDef, CompilableDef):
    generic_args: Mapping[str, Argument]
    trace: "Trace"

    @override
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
        add_metadata(
            module.hugr[func_def].metadata,
            self.metadata,
        )
        if debug_mode_enabled():
            module.hugr[func_def].metadata[HugrDebugInfo] = make_subprogram_record(
                self.defined_at, ctx
            )
        return CompiledTracedFunctionDef(
            self.id,
            self.name,
            self.defined_at,
            self.ty,
            self.python_func,
            self.generic_args,
            self.trace,
            func_def,
            unitary_flags=self.unitary_flags,
            metadata=self.metadata,
        )


@dataclass(frozen=True)
class CompiledTracedFunctionDef(
    TracedMonoFunctionDef, CompiledCallableDef, CompiledHugrNodeDef
):
    func_def: hf.Function

    @override
    @property
    def call_effects(self) -> frozenset[Effect]:
        """The maximum set of effects that may occur when calling the function."""
        # For now, an approximation. (We said, may occur.)
        # TODO refine via callgraph: https://github.com/Quantinuum/guppylang/issues/1748
        return frozenset([Effect.ANY])

    @property
    def hugr_node(self) -> Node:
        """The Hugr node this definition was compiled into."""
        return self.func_def.parent_node

    @override
    def load(self, dfg: DFContainer, ctx: CompilerContext, node: AstNode) -> Wire:
        """Loads the function as a value into a local Hugr dataflow graph."""
        type_args: Inst = ()  # Comptime functions are not generic
        func_ty: ht.FunctionType = self.ty.instantiate(type_args).to_hugr(ctx)
        hugr_type_args: list[ht.TypeArg] = [arg.to_hugr(ctx) for arg in type_args]
        return dfg.builder.load_function(self.func_def, func_ty, hugr_type_args)

    @override
    def compile_call(
        self,
        args: list[Wire],
        dfg: DFContainer,
        ctx: CompilerContext,
        node: AstNode,
    ) -> CallReturnWires:
        """Compiles a call to the function."""
        num_returns = len(type_to_row(self.ty.output))
        with dfg.builder.set_ast_context(node):
            call = dfg.builder.call(self.func_def, *args, effects=self.call_effects)
        return CallReturnWires(
            regular_returns=list(call[:num_returns]),
            inout_returns=list(call[num_returns:]),
        )

    @override
    def compile_inner(self, ctx: CompilerContext) -> None:
        """Replays the trace recorded while the function was checked."""
        builder = FunctionBuilder(self.func_def)
        wires: dict[tuple[int, int], Wire] = {
            (-1, port): wire for port, wire in enumerate(builder.inputs())
        }

        def get_wire(ref: TraceWire) -> Wire:
            return wires[ref.entry, ref.port]

        for entry_index, entry in enumerate(self.trace.operations):
            outputs: Sequence[Wire]
            match entry:
                case TraceOperation(op, inputs, output_count, effects, node):
                    with builder.set_ast_context(node):
                        node = builder.add_op(
                            (op, effects), *(get_wire(i) for i in inputs)
                        )
                        outputs = [node[i] for i in range(output_count)]
                case TraceLoad(value, node):
                    if isinstance(value, val.Value):
                        outputs = [builder.load(value)[0]]
                    else:
                        defn = ctx.build_compiled_def(value, type_args=())
                        # TypeDefs should already have been converted to LoadFunctions
                        # of their *constructors* during checking/tracing.
                        if not isinstance(defn, CompiledValueDef):
                            def_kind = defn.description.capitalize()
                            err = f"{def_kind} `{defn.name}` is not a value"
                            raise GuppyComptimeError(err)
                        outputs = [defn.load(DFContainer(builder, ctx), ctx, node)]
                    output_count = 1
                case TraceFunctionLoad(def_id, type_args, node):
                    defn = ctx.build_compiled_def(def_id, type_args)
                    assert isinstance(defn, CompiledValueDef)
                    outputs = [defn.load(DFContainer(builder, ctx), ctx, node)]
                    output_count = 1
                case TraceCall(def_id, type_args, inputs, output_count, node):
                    func = ctx.build_compiled_def(def_id, type_args)
                    assert isinstance(func, CompiledCallableDef)
                    returns = func.compile_call(
                        [get_wire(i) for i in inputs],
                        DFContainer(builder, ctx),
                        ctx,
                        node,
                    )
                    outputs = [*returns.regular_returns, *returns.inout_returns]
                case _:
                    assert_never(entry)

            assert len(outputs) == output_count
            for port, wire in enumerate(outputs):
                wires[entry_index, port] = wire

        builder.set_outputs(*(get_wire(output) for output in self.trace.outputs))
