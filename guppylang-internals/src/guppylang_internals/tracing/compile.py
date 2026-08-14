import hugr.build.function as hf
from hugr import Wire
from typing_extensions import assert_never

from guppylang_internals.checker.core import ComptimeVariable
from guppylang_internals.compiler.builder import FunctionBuilder, ops
from guppylang_internals.compiler.core import CompilerContext, DFContainer
from guppylang_internals.compiler.expr_compiler import (
    ExprCompiler,
    python_value_to_hugr,
)
from guppylang_internals.definition.value import CompiledValueDef, ValueDef
from guppylang_internals.std._internal.compiler.array import array_new, array_unpack
from guppylang_internals.tracing.recorder import (
    Trace,
    TraceCall,
    TraceFunctionLoad,
    TraceLoad,
    TraceLoadVal,
    TraceMakeTuple,
    TraceNewArray,
    TraceOutput,
    TraceUnpackArray,
    TraceUntuple,
)


def replay_trace(func_def: hf.Function, trace: Trace, ctx: CompilerContext) -> None:
    """Replays a traced function's recorded operations into its Hugr definition."""
    builder = FunctionBuilder(func_def)
    dfg = DFContainer(builder, ctx)
    comp = ExprCompiler(ctx)

    wires: dict[tuple[int, int], Wire] = {
        (-1, port): wire for port, wire in enumerate(builder.inputs())
    }

    def get_wire(ref: TraceOutput) -> Wire:
        return (
            dfg[ref]
            if isinstance(ref, ComptimeVariable)
            else wires[ref.entry, ref.port]
        )

    for entry_index, entry in enumerate(trace.operations):
        outputs: list[Wire]
        match entry:
            case TraceUntuple(types, input):
                hugr_types = [ty.to_hugr(ctx) for ty in types]
                node = builder.add_op(ops.unpack_tuple(hugr_types), get_wire(input))
                outputs = [node[i] for i in range(len(types))]
            case TraceMakeTuple(inputs):
                node = builder.add_op(ops.make_tuple(), *(get_wire(i) for i in inputs))
                outputs = [node[0]]
            case TraceUnpackArray(elem_ty, length, input):
                hugr_elem_ty = elem_ty.to_hugr(ctx)
                node = builder.add_op(
                    array_unpack(hugr_elem_ty, length), get_wire(input)
                )
                outputs = [node[i] for i in range(length)]
            case TraceNewArray(elem_ty, inputs):
                hugr_elem_ty = elem_ty.to_hugr(ctx)
                node = builder.add_op(
                    array_new(hugr_elem_ty, len(inputs)),
                    *(get_wire(i) for i in inputs),
                )
                outputs = [node[0]]
            case TraceLoadVal(value, ty, node):
                hugr_val = python_value_to_hugr(value, ty, ctx)
                assert hugr_val is not None
                outputs = [builder.load(hugr_val)[0]]
            case TraceLoad(v_def, node):
                _v: ValueDef = v_def  # TypeDefs already converted to LoadFunctions
                defn = ctx.build_compiled_def(v_def.id, type_args=())
                assert isinstance(defn, CompiledValueDef)
                outputs = [defn.load(DFContainer(builder, ctx), ctx, node)]
            case TraceFunctionLoad(def_id, type_args, node):
                defn = ctx.build_compiled_def(def_id, type_args)
                assert isinstance(defn, CompiledValueDef)
                outputs = [defn.load(DFContainer(builder, ctx), ctx, node)]
            case TraceCall(call_node, input_places):
                for arg, val in input_places:
                    dfg[arg] = get_wire(val)
                outputs = [comp.compile(call_node, dfg)]
            case _:
                assert_never(entry)

        for port, wire in enumerate(outputs):
            wires[entry_index, port] = wire

    builder.set_outputs(*(get_wire(output) for output in trace.outputs))
