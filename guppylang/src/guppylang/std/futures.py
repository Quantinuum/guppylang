"""Guppy standard library for future type and its operations"""

from typing import Generic, no_type_check

from guppylang_internals.decorator import custom_type, hugr_op
from guppylang_internals.std._internal.compiler.futures import future_op, future_to_hugr
from guppylang_internals.tys.param import TypeParam

from guppylang import guppy
from guppylang.std.lang import owned

T = guppy.type_var("T", copyable=False, droppable=False)

_future_params = [TypeParam(0, "T", must_be_copyable=False, must_be_droppable=False)]


@custom_type(future_to_hugr, copyable=False, droppable=False, params=_future_params)
class Future(Generic[T]):  # type: ignore[misc]
    """A value of type `T` that is computed asynchronously."""

    @hugr_op(future_op("Read"))
    @no_type_check
    def read(self: "Future[T]" @ owned) -> T:
        """Reads a value from a future, consuming it."""

    @hugr_op(future_op("Dup"))
    @no_type_check
    def copy(self: "Future[T]") -> "Future[T]":
        """Duplicate a future."""

    @hugr_op(future_op("Free"))
    @no_type_check
    def discard(self: "Future[T]" @ owned) -> None:
        """Discards a future without reading it."""
