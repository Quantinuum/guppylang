import ast
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeAlias, overload

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.core import ComptimeVariable, Place
from guppylang_internals.definition.value import ValueDef
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


#: A value usable as an input to an op/call in a trace, i.e. that will be resolved
#: to a Hugr `Wire` during compilation. (`ComptimeVariable`s are resolved via the
#: state held in the DFContainer.)
TraceOutput: TypeAlias = TraceWire | ComptimeVariable


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
    TraceUntuple
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


class TraceRecorder:
    """Records the actions performed by a comptime function."""

    def __init__(self, input_count: int) -> None:
        self._inputs = tuple(TraceWire(-1, port) for port in range(input_count))
        self._operations: list[TraceEntry] = []
        self._outputs: tuple[TraceOutput, ...] | None = None

    def inputs(self) -> tuple[TraceWire, ...]:
        return self._inputs

    def record_untuple(
        self, types: Sequence[Type], input: TraceOutput
    ) -> Sequence[TraceWire]:
        """Records a tuple unpack to replay into the Hugr during compilation."""
        return self._add(TraceUntuple(types, input))

    def record_make_tuple(self, *inputs: TraceOutput) -> TraceWire:
        """Records a make-tuple to replay into the Hugr during compilation."""
        return self._add(TraceMakeTuple(inputs))

    def record_unpack_array(
        self, elem_ty: Type, length: int, input: TraceOutput
    ) -> Sequence[TraceWire]:
        """Records an array unpack to replay into the Hugr during compilation."""
        return self._add(TraceUnpackArray(elem_ty, length, input))

    def record_new_array(self, elem_ty: Type, *inputs: TraceOutput) -> TraceWire:
        """Records a new-array op to replay into the Hugr during compilation."""
        return self._add(TraceNewArray(elem_ty, inputs))

    def record_load_val(self, value: Any, ty: Type, node: AstNode) -> TraceWire:
        """Records a load to replay into the Hugr during compilation"""
        return self._add(TraceLoadVal(value, ty, node))

    def record_load(self, value: ValueDef) -> TraceWire:
        """Records a load to replay into the Hugr during compilation"""
        from guppylang_internals.tracing.state import get_tracing_state

        node = get_tracing_state().node
        return self._add(TraceLoad(value, node))

    def record_load_func(self, def_id: "DefId", type_args: "Inst") -> TraceWire:
        """Records a load_function to replay into the Hugr during compilation"""
        from guppylang_internals.tracing.state import get_tracing_state

        node = get_tracing_state().node
        return self._add(TraceFunctionLoad(def_id, type_args, node))

    def record_call(
        self,
        node: ast.expr,
        input_places: Sequence[tuple[Place, TraceWire]],
    ) -> TraceWire:
        """Records a function call to be compiled into the Hugr during replay"""
        return self._add(TraceCall(node, input_places))

    def set_outputs(self, *outputs: TraceOutput) -> None:
        self._outputs = tuple(outputs)

    def finish(self) -> Trace:
        assert self._outputs is not None, "Traced function did not set outputs"
        return Trace(tuple(self._operations), self._outputs)

    @overload
    def _add(self, entry: TraceUnpackArray | TraceUntuple) -> Sequence[TraceWire]: ...
    @overload
    def _add(
        self,
        entry: TraceNewArray
        | TraceMakeTuple
        | TraceLoad
        | TraceLoadVal
        | TraceFunctionLoad
        | TraceCall,
    ) -> TraceWire: ...

    def _add(self, entry: TraceEntry) -> TraceWire | Sequence[TraceWire]:
        entry_index = len(self._operations)
        self._operations.append(entry)
        match entry:
            case TraceUnpackArray(length=output_count):
                pass
            case TraceUntuple(types=types):
                output_count = len(types)
            case _:
                return TraceWire(entry_index, 0)
        return [TraceWire(entry_index, port) for port in range(output_count)]
