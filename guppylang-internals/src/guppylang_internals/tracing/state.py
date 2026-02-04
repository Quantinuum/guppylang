from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.core import Globals
from guppylang_internals.compiler.core import CompilerContext, DFContainer
from guppylang_internals.error import InternalGuppyError

if TYPE_CHECKING:
    from guppylang_internals.tracing.object import GuppyObject, GuppyObjectId


@dataclass
class TracingState:
    """Internal state that is used during the tracing phase of comptime functions."""

    #: Reference to the global compilation context.
    ctx: CompilerContext

    #: The current dataflow graph under construction.
    dfg: DFContainer

    #: An AST node capturing the code block that is currently being traced
    node: AstNode

    #: Set of all allocated undroppable GuppyObjects where the `used` flag is not set,
    #: indexed by their id. This is used to detect linearity violations.
    unused_undroppable_objs: "dict[GuppyObjectId, GuppyObject]" = field(
        default_factory=dict
    )

    @property
    def globals(self) -> Globals:
        return self.ctx.checked_globals


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
    yield
    _STATE.reset(token)
