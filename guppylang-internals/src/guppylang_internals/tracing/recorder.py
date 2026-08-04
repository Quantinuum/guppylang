import ast
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeAlias, overload

from hugr.ops import DataflowOp

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.core import ComptimeVariable, Place
from guppylang_internals.compiler.builder import OpWithEffects
from guppylang_internals.definition.value import ValueDef
from guppylang_internals.error import InternalGuppyError
from guppylang_internals.tys.ty import Type

if TYPE_CHECKING:
    from guppylang_internals.definition.common import DefId
    from guppylang_internals.tys.subst import Inst


@dataclass(frozen=True)
class TraceWire:
    """Reference to an output port of an op explicitly recorded in a comptime trace.

    Entry ``-1`` denotes an input of the traced function;
     all other entries index `TraceEntry`s.
    """

    entry: int
    port: int

    def as_trace_wire(self) -> "TraceWire":
        return self


#: A value usable as an input to an op/call in a trace, i.e. that will be resolved
#: to a Hugr `Wire` during compilation. (`ComptimeVariable`s are resolved via the
#: state held in the DFContainer.)
TraceOutput: TypeAlias = TraceWire | ComptimeVariable


@dataclass(frozen=True)
class TraceOperation:
    """A primitive dataflow operation emitted while tracing."""

    op: OpWithEffects
    inputs: tuple[TraceOutput, ...]
    output_count: int
    node: AstNode | None


@dataclass(frozen=True)
class TraceUntuple:
    """A tuple unpack operation emitted while tracing."""

    types: Sequence[Type]
    input: TraceOutput


@dataclass(frozen=True)
class TraceMakeTuple:
    """A make-tuple operation emitted while tracing."""

    inputs: Sequence[TraceOutput]


@dataclass(frozen=True)
class TraceNewArray:
    """A new array operation emitted while tracing."""

    elem_ty: Type
    inputs: Sequence[TraceOutput]


@dataclass(frozen=True)
class TraceUnpackArray:
    """An array unpack operation emitted while tracing."""

    elem_ty: Type
    length: int
    input: TraceOutput


@dataclass(frozen=True)
class TraceLoadVal:
    """A python value loaded while tracing."""

    value: Any
    ty: Type
    node: AstNode


@dataclass(frozen=True)
class TraceLoad:
    """A comptime value loaded while tracing."""

    value: ValueDef
    node: AstNode


@dataclass(frozen=True)
class TraceFunctionLoad:
    """A function value loaded while tracing."""

    def_id: "DefId"
    type_args: "Inst"
    node: AstNode


@dataclass(frozen=True)
class TraceCall:
    """A resolved Guppy function call emitted while tracing."""

    call_node: ast.expr
    input_places: Sequence[tuple[Place, TraceWire]]


TraceEntry = (
    TraceOperation
    | TraceUntuple
    | TraceMakeTuple
    | TraceUnpackArray
    | TraceNewArray
    | TraceLoad
    | TraceLoadVal
    | TraceFunctionLoad
    | TraceCall
)


@dataclass(frozen=True)
class Trace:
    """Replayable dataflow trace of a monomorphic comptime function."""

    operations: tuple[TraceEntry, ...]
    outputs: tuple[TraceOutput, ...]


class TraceNode(Sequence[TraceWire]):
    """Virtual node returned by :class:`TraceRecorder`."""

    def __init__(self, wires: Sequence[TraceWire]) -> None:
        self._wires = tuple(wires)

    @overload
    def __getitem__(self, index: int) -> TraceWire: ...
    @overload
    def __getitem__(self, index: slice) -> tuple[TraceWire, ...]: ...

    def __getitem__(self, index: int | slice) -> TraceWire | tuple[TraceWire, ...]:
        return self._wires[index]

    def __len__(self) -> int:
        return len(self._wires)

    def outputs(self) -> tuple[TraceWire, ...]:
        return self._wires

    def as_trace_wire(self) -> TraceWire:
        if len(self._wires) != 1:
            raise InternalGuppyError(
                "Cannot convert TraceNode with multiple outputs to a single TraceWire"
            )
        return self._wires[0]


class TraceRecorder:
    """Records the actions performed by a comptime function."""

    def __init__(self, input_count: int) -> None:
        self._inputs = tuple(TraceWire(-1, port) for port in range(input_count))
        self._operations: list[TraceEntry] = []
        self._outputs: tuple[TraceOutput, ...] | None = None

    def inputs(self) -> tuple[TraceWire, ...]:
        return self._inputs

    def record_op(self, op: OpWithEffects, /, *args: TraceOutput) -> TraceNode:
        """Records a dataflow operation to replay into the Hugr during compilation"""
        from guppylang_internals.tracing.state import get_tracing_state

        (dataflow_op, _effects) = op
        output_count = _operation_output_count(dataflow_op)
        node = get_tracing_state().node
        return self._add(
            TraceOperation(
                op,
                tuple(args),
                output_count,
                node,
            )
        )

    def record_untuple(self, types: Sequence[Type], input: TraceOutput) -> TraceNode:
        """Records a tuple unpack to replay into the Hugr during compilation."""
        return self._add(TraceUntuple(types, input))

    def record_make_tuple(self, *inputs: TraceOutput) -> TraceWire:
        """Records a make-tuple to replay into the Hugr during compilation."""
        return self._add(TraceMakeTuple(inputs)).as_trace_wire()

    def record_unpack_array(
        self, elem_ty: Type, length: int, input: TraceOutput
    ) -> TraceNode:
        """Records an array unpack to replay into the Hugr during compilation."""
        return self._add(TraceUnpackArray(elem_ty, length, input))

    def record_new_array(self, elem_ty: Type, *inputs: TraceOutput) -> TraceWire:
        """Records a new-array op to replay into the Hugr during compilation."""
        return self._add(TraceNewArray(elem_ty, inputs)).as_trace_wire()

    def record_load_val(self, value: Any, ty: Type, node: AstNode) -> TraceWire:
        """Records a load to replay into the Hugr during compilation"""
        return self._add(TraceLoadVal(value, ty, node)).as_trace_wire()

    def record_load(self, value: ValueDef) -> TraceWire:
        """Records a load to replay into the Hugr during compilation"""
        from guppylang_internals.tracing.state import get_tracing_state

        node = get_tracing_state().node
        return self._add(TraceLoad(value, node)).as_trace_wire()

    def record_load_func(self, def_id: "DefId", type_args: "Inst") -> TraceWire:
        """Records a load_function to replay into the Hugr during compilation"""
        from guppylang_internals.tracing.state import get_tracing_state

        node = get_tracing_state().node
        return self._add(TraceFunctionLoad(def_id, type_args, node)).as_trace_wire()

    def record_call(
        self,
        node: ast.expr,
        input_places: Sequence[tuple[Place, TraceWire]],
    ) -> TraceWire:
        """Records a function call to be compiled into the Hugr during replay"""
        return self._add(TraceCall(node, input_places)).as_trace_wire()

    def set_outputs(self, *outputs: TraceOutput) -> None:
        self._outputs = tuple(outputs)

    def finish(self) -> Trace:
        assert self._outputs is not None, "Traced function did not set outputs"
        return Trace(tuple(self._operations), self._outputs)

    def _add(self, entry: TraceEntry) -> TraceNode:
        entry_index = len(self._operations)
        self._operations.append(entry)
        match entry:
            case (
                TraceOperation(output_count=output_count)
                | TraceUnpackArray(length=output_count)
            ):
                pass
            case TraceUntuple(types=types):
                output_count = len(types)
            case _:
                output_count = 1
        return TraceNode([TraceWire(entry_index, port) for port in range(output_count)])


def _operation_output_count(op: DataflowOp) -> int:
    """Returns the statically known number of value outputs for traceable ops."""
    from hugr import ops as hops

    match op:
        case hops.MakeTuple() | hops.LoadConst():
            return 1
        case hops.UnpackTuple(types=types):
            return len(types)
        case _:
            signature = getattr(op, "signature", None)
            if signature is not None:
                return len(signature.output)
            raise InternalGuppyError(
                f"Cannot record operation `{type(op).__name__}` during comptime tracing"
            )
