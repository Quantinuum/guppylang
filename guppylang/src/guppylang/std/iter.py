"""Utilities for iteration over collections of values."""

# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def"

from __future__ import annotations

from typing import TYPE_CHECKING, Any, no_type_check

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

    @custom_function(NoopCompiler())
    def __new__(iterator: L @ owned) -> SizedIter[L, n]:  # type: ignore[type-arg]
        """Casts an iterator into a `SizedIter`."""

    @custom_function(NoopCompiler())
    def unwrap_iter(self: SizedIter[L, n] @ owned) -> L:
        """Extracts the actual iterator."""

    @custom_function(NoopCompiler())
    def __iter__(self: SizedIter[L, n] @ owned) -> SizedIter[L, n]:  # type: ignore[type-arg]
        """Dummy implementation making sized iterators iterable themselves."""


@guppy.struct
class Range:
    next: int
    stop: int
    step: int

    @guppy
    def __iter__(self: Range) -> Range:
        return self

    @guppy
    @no_type_check
    def __next__(self: Range) -> Option[tuple[int, Range]]:
        end = (self.next >= self.stop) if self.step >= 0 else (self.next <= self.stop)
        if end:
            return nothing()
        return some((self.next, Range(self.next + self.step, self.stop, self.step)))


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
    """
