import ast
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, overload

from hugr import val
from hugr.ops import DataflowOp

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.core import ComptimeVariable, Place
from guppylang_internals.compiler.builder import OpWithEffects
from guppylang_internals.definition.common import DefId
from guppylang_internals.error import InternalGuppyError
from guppylang_internals.tys.common import ToHugrContext

if TYPE_CHECKING:
    from guppylang_internals.definition.traced import TracedFunctionDef
    from guppylang_internals.tracing.object import GuppyObject, GuppyObjectId
    from guppylang_internals.tys.subst import Inst


@dataclass
class TracingState:
    """Internal state that is used during the tracing phase of comptime functions."""

    #: Context used to translate Guppy types into HUGR types.
    ctx: ToHugrContext

    #: The trace of operations performed during the comptime execution of a function.
    builder: "TraceRecorder"

    #: An AST node capturing the code block that is currently being traced
    node: AstNode

    #: The function definition currently being traced.
    function_definition: "TracedFunctionDef"  # quotes to avoid circular import

    #: Set of all allocated undroppable GuppyObjects where the `used` flag is not set,
    #: indexed by their id. This is used to detect linearity violations.
    unused_undroppable_objs: "dict[GuppyObjectId, GuppyObject]" = field(
        default_factory=dict
    )


_STATE: ContextVar[TracingState | None] = ContextVar("_STATE", default=None)


def reset_state() -> None:
    """Resets the tracing state to be undefined."""
    _STATE.set(None)


def tracing_active() -> bool:
    """Checks if the tracing mode is currently active."""
    return _STATE.get() is not None


def get_tracing_state() -> TracingState:
    """Returns the current tracing state.

    Raises an `InternalGuppyError` if the tracing mode is currently not active.
    """
    state = _STATE.get()
    if state is None:
        raise InternalGuppyError("Guppy tracing mode is not active")
    return state


@contextmanager
def set_tracing_state(state: TracingState) -> Iterator[None]:
    """Context manager to update tracing state for the duration of a code block."""
    token = _STATE.set(state)
    try:
        yield
    finally:
        _STATE.reset(token)


@dataclass(frozen=True)
class TraceWire:
    """Reference to an output port in a comptime trace.

    Entry ``-1`` denotes an input of the traced function;
     all other entries index `TraceEntry`s.
    """

    entry: int
    port: int

    def as_trace_wire(self) -> "TraceWire":
        return self


@dataclass(frozen=True)
class TraceOperation:
    """A primitive dataflow operation emitted while tracing."""

    op: OpWithEffects
    inputs: tuple[TraceWire | ComptimeVariable, ...]
    output_count: int
    node: AstNode | None


@dataclass(frozen=True)
class TraceLoad:
    """A HUGR value loaded while tracing."""

    value: val.Value | DefId
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


TraceEntry = TraceOperation | TraceLoad | TraceFunctionLoad | TraceCall


@dataclass(frozen=True)
class Trace:
    """Replayable dataflow trace of a monomorphic comptime function."""

    operations: tuple[TraceEntry, ...]
    outputs: tuple[TraceWire | ComptimeVariable, ...]


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
    """Records the builder actions performed by a comptime function."""

    def __init__(self, input_count: int) -> None:
        self._inputs = tuple(TraceWire(-1, port) for port in range(input_count))
        self._operations: list[TraceEntry] = []
        self._outputs: tuple[TraceWire | ComptimeVariable, ...] | None = None

    def inputs(self) -> tuple[TraceWire, ...]:
        return self._inputs

    def add_op(
        self, op: OpWithEffects, /, *args: TraceWire | ComptimeVariable
    ) -> TraceNode:
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

    def load(self, value: val.Value | DefId) -> TraceWire:
        node = get_tracing_state().node
        return self._add(TraceLoad(value, node)).as_trace_wire()

    def load_function(self, def_id: "DefId", type_args: "Inst") -> TraceWire:
        node = get_tracing_state().node
        return self._add(TraceFunctionLoad(def_id, type_args, node)).as_trace_wire()

    def call(
        self,
        node: ast.expr,
        input_places: Sequence[tuple[Place, TraceWire]],
    ) -> TraceWire:
        return self._add(TraceCall(node, input_places)).as_trace_wire()

    def set_outputs(self, *outputs: TraceWire | ComptimeVariable) -> None:
        self._outputs = tuple(outputs)

    def finish(self) -> Trace:
        assert self._outputs is not None, "Traced function did not set outputs"
        return Trace(tuple(self._operations), self._outputs)

    def _add(self, entry: TraceEntry) -> TraceNode:
        entry_index = len(self._operations)
        self._operations.append(entry)
        output_count = entry.output_count if isinstance(entry, TraceOperation) else 1
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
