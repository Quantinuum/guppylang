from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from guppylang_internals.ast_util import AstNode
from guppylang_internals.definition.traced import TracedFunctionDef
from guppylang_internals.error import InternalGuppyError
from guppylang_internals.tracing.builder import TraceBuilder
from guppylang_internals.tys.common import ToHugrContext

if TYPE_CHECKING:
    from guppylang_internals.tracing.object import GuppyObject, GuppyObjectId


@dataclass
class TracingState:
    """Internal state that is used during the tracing phase of comptime functions."""

    #: Context used to translate Guppy types into HUGR types.
    ctx: ToHugrContext | None

    #: The trace of operations performed during the comptime execution of a function.
    builder: TraceBuilder

    #: An AST node capturing the code block that is currently being traced
    node: AstNode

    #: The function definition currently being traced.
    function_definition: TracedFunctionDef

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
