from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, overload

from hugr import val
from hugr.ops import DataflowOp

from guppylang_internals.ast_util import AstNode
from guppylang_internals.compiler.builder import OpWithEffects
from guppylang_internals.error import (
    InternalGuppyError,
)

if TYPE_CHECKING:

    from guppylang_internals.definition.common import DefId
    from guppylang_internals.tys import Effect
    from guppylang_internals.tys.subst import Inst


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

    op: DataflowOp
    inputs: tuple[TraceWire, ...]
    output_count: int
    effects: tuple["Effect", ...]
    node: AstNode | None


@dataclass(frozen=True)
class TraceLoad:
    """A HUGR value loaded while tracing."""

    value: val.Value
    node: AstNode | None


@dataclass(frozen=True)
class TraceFunctionLoad:
    """A function value loaded while tracing."""

    def_id: "DefId"
    type_args: "Inst"
    node: AstNode  # | None


@dataclass(frozen=True)
class TraceCall:
    """A resolved Guppy function call emitted while tracing."""

    def_id: "DefId"
    type_args: "Inst"
    inputs: tuple[TraceWire, ...]
    output_count: int
    node: AstNode


TraceEntry = TraceOperation | TraceLoad | TraceFunctionLoad | TraceCall


@dataclass(frozen=True)
class Trace:
    """Replayable dataflow trace of a monomorphic comptime function."""

    operations: tuple[TraceEntry, ...]
    outputs: tuple[TraceWire, ...]


class TraceNode(Sequence[TraceWire]):
    """Virtual node returned by :class:`TraceBuilder`."""

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


class TraceBuilder:
    """Records the builder actions performed by a comptime function."""

    current_ast_node: AstNode | None

    def __init__(self, input_count: int) -> None:
        self.current_ast_node = None
        self._inputs = tuple(TraceWire(-1, port) for port in range(input_count))
        self._operations: list[TraceEntry] = []
        self._outputs: tuple[TraceWire, ...] | None = None

    def inputs(self) -> tuple[TraceWire, ...]:
        return self._inputs

    @contextmanager
    def set_ast_context(self, node: AstNode | None) -> Iterator[None]:
        previous = self.current_ast_node
        self.current_ast_node = node
        try:
            yield
        finally:
            self.current_ast_node = previous

    def add_op(
        self, op: OpWithEffects, /, *args: TraceWire | TraceNode, **_: Any
    ) -> TraceNode:
        dataflow_op, effects = op
        output_count = _operation_output_count(dataflow_op)
        return self._add(
            TraceOperation(
                dataflow_op,
                tuple(arg.as_trace_wire() for arg in args),
                output_count,
                tuple(effects),
                self.current_ast_node,
            )
        )

    def load(self, value: val.Value, *_: Any, **__: Any) -> TraceWire:
        return self._add(TraceLoad(value, self.current_ast_node)).as_trace_wire()

    def load_function(self, def_id: "DefId", type_args: "Inst") -> TraceNode:
        assert self.current_ast_node is not None
        return self._add(TraceFunctionLoad(def_id, type_args, self.current_ast_node))

    def call(
        self,
        def_id: "DefId",
        type_args: "Inst",
        output_count: int,
        *args: TraceWire | TraceNode,
        node: AstNode,
    ) -> TraceNode:
        return self._add(
            TraceCall(
                def_id,
                type_args,
                tuple(arg.as_trace_wire() for arg in args),
                output_count,
                node,
            )
        )

    def set_outputs(self, *outputs: TraceWire | TraceNode) -> None:
        self._outputs = tuple(output.as_trace_wire() for output in outputs)

    def finish(self) -> Trace:
        assert self._outputs is not None, "Traced function did not set outputs"
        return Trace(tuple(self._operations), self._outputs)

    def _add(self, entry: TraceEntry) -> TraceNode:
        entry_index = len(self._operations)
        self._operations.append(entry)
        output_count = (
            entry.output_count if isinstance(entry, TraceOperation | TraceCall) else 1
        )
        return TraceNode([TraceWire(entry_index, port) for port in range(output_count)])


def _operation_output_count(op: DataflowOp) -> int:
    """Returns the statically known number of value outputs for traceable ops."""
    from hugr import ops as hops

    match op:
        case hops.MakeTuple() | hops.LoadConst():
            return 1
        case hops.UnpackTuple(types=types):
            return len(types or ())
        case _:
            signature = getattr(op, "signature", None)
            if signature is not None and hasattr(signature, "output"):
                return len(signature.output)
            raise InternalGuppyError(
                f"Cannot record operation `{type(op).__name__}` during comptime tracing"
            )
