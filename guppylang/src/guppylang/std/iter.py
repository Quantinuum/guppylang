"""Utilities for iteration over collections of values."""

# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def"

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self, no_type_check

from guppylang_internals.decorator import custom_function, extend_type
from guppylang_internals.definition.custom import NoopCompiler
from guppylang_internals.tys.builtin import sized_iter_type_def

from guppylang import guppy
from guppylang.std.option import Option, nothing, some

if TYPE_CHECKING:
    from guppylang.std.lang import comptime, owned
    from guppylang.std.num import nat

L = guppy.type_var("L", copyable=False, droppable=False)
n = guppy.nat_var("n")


@extend_type(sized_iter_type_def)
class SizedIter:
    """A wrapper around an iterator type `L` promising that the iterator will yield
    exactly `n` values.

    Annotating an iterator with an incorrect size is undefined behaviour.
    """

    def __class_getitem__(cls, item: Any) -> type:
        # Dummy implementation to allow subscripting of the `SizedIter` type in
        # positions that are evaluated by the Python interpreter
        return cls

    @custom_function(NoopCompiler(), effects=())
    def __new__(iterator: L @ owned) -> SizedIter[L, n]:  # type: ignore[type-arg]
        """Casts an iterator into a `SizedIter`."""

    @custom_function(NoopCompiler(), effects=())
    def unwrap_iter(self: SizedIter[L, n] @ owned) -> L:
        """Extracts the actual iterator."""

    @custom_function(NoopCompiler(), effects=())
    def __iter__(self: SizedIter[L, n] @ owned) -> SizedIter[L, n]:  # type: ignore[type-arg]
        """Dummy implementation making sized iterators iterable themselves."""


@guppy.struct
class Range:
    _next: int
    _stop: int
    _step: int

    @guppy
    @no_type_check
    def __iter__(self: Self @ owned) -> Self:
        return self

    @guppy
    @no_type_check
    def __next__(self: Self @ owned) -> Option[tuple[int, Self]]:
        end = (
            (self._next >= self._stop)
            if self._step >= 0
            else (self._next <= self._stop)
        )
        if end:
            return nothing()
        actual_next = self._next
        self._next += self._step
        return some((actual_next, self))

    @guppy
    @no_type_check
    def __reversed__(self: Self) -> None:
        if self._step == 0:
            panic("Range.__reversed__: step is zero")

        diff = self._stop - self._next

        # The range is empty when diff and step have different signs,
        # or when the difference is zero.
        if diff == 0 or (diff < 0) != (self._step < 0):
            last = self._next
            self._stop = self._next
        else:
            distance = diff if diff >= 0 else -diff
            step = self._step if self._step >= 0 else -self._step
            count = (distance + step - 1) // step
            last = self._next + (count - 1) * self._step
            self._stop = self._next - self._step

        self._next = last
        self._step = -self._step


@guppy
@no_type_check
def _range1(stop: int) -> Range:
    return Range(0, stop, 1)


@guppy
@no_type_check
def _range2(start: int, stop: int) -> Range:
    return Range(start, stop, 1)


@guppy
@no_type_check
def _range3(start: int, stop: int, step: int) -> Range:
    if step == 0:
        panic("range() arg 3 must not be zero")
    return Range(start, stop, step)


@guppy
@no_type_check
def _range_comptime(stop: nat @ comptime) -> "SizedIter[Range, stop]":  # noqa: F821 UP037
    return SizedIter(Range(0, stop, 1))


@guppy.overload(_range_comptime, _range1, _range2, _range3)
def range(start: int, stop: int = 0, step: int = 1) -> Range:
    """An iterator that yields a sequence of integers.

    Behaves like the builtin Python `range` function. Concretely, the ``i``th yielded
    number is ``start + i * step``. Numbers are yielded as long as they are

    * ``< stop`` in the case where ``step >= 0``, or
    * ``> stop`` otherwise.

    ``start`` defaults to ``0`` and ``step`` defaults to ``1``. If the provided ``stop``
    value is comptime known, then the returned iterator will have a static size
    annotation and may for example be used inside array comprehensions.

    Iterating with a ``step`` of ``0`` raises a runtime panic.
    """


# Delayed import to avoid cyclic import since `iter` is loaded very early via
# `builtins`/`array` (which import `SizedIter` from this module).
from guppylang.std.platform import panic  # noqa: E402
