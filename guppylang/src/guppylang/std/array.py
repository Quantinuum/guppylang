"""Utilities for fixed-size arrays, denoted `array[T, n]`, for element type `T` and
compile-time constant size `n`.

See `frozenarray[T, n]` for an immutable version of the `array[T, n]` type.
"""

# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def"

from __future__ import annotations

import builtins
from types import GeneratorType
from typing import TYPE_CHECKING, Generic, TypeVar, no_type_check

from guppylang_internals.decorator import custom_function, extend_type
from guppylang_internals.definition.custom import CopyInoutCompiler
from guppylang_internals.std._internal.checker import (
    ArrayCopyChecker,
    ArrayIndexChecker,
    NewArrayChecker,
)
from guppylang_internals.std._internal.compiler.array import (
    ArrayDiscardAllUsedCompiler,
    ArrayGetitemCompiler,
    ArrayIsBorrowedCompiler,
    ArraySetitemCompiler,
    ArraySwapCompiler,
    NewArrayCompiler,
)
from guppylang_internals.std._internal.compiler.frozenarray import (
    FrozenarrayGetitemCompiler,
)
from guppylang_internals.tys.builtin import array_type_def, frozenarray_type_def

from guppylang import guppy
from guppylang.std.err import Result, err, ok
from guppylang.std.iter import SizedIter
from guppylang.std.option import Option, nothing, some

if TYPE_CHECKING:
    from guppylang.std.lang import owned


T = guppy.type_var("T")
L = guppy.type_var("L", copyable=False, droppable=False)
n = guppy.nat_var("n")

_T = TypeVar("_T")
_n = TypeVar("_n")


@extend_type(
    array_type_def,
    # Instruct the decorator to return the original class instead of the Guppy array
    # definition. This allows us to customise the runtime behaviour of arrays in
    # comptime to behave like lists.
    return_class=True,
)
class array(builtins.list[_T], Generic[_T, _n]):
    """Sequence of homogeneous values with statically known fixed length."""

    @custom_function(ArrayGetitemCompiler(), checker=ArrayIndexChecker())
    def __getitem__(self: array[L, n], idx: int) -> L: ...

    @custom_function(ArraySetitemCompiler(), checker=ArrayIndexChecker())
    def __setitem__(self: array[L, n], idx: int, value: L @ owned) -> None: ...

    @guppy
    @no_type_check
    def __len__(self: array[L, n]) -> int:
        return n

    @custom_function(NewArrayCompiler(), NewArrayChecker(), higher_order_value=False)
    def __new__(): ...

    # `__new__` will be overwritten below to provide actual runtime behaviour for
    # comptime. We still need to hold on to a reference to the Guppy function so
    # `@extend_type` can find it
    __new_guppy__ = __new__

    @guppy
    @no_type_check
    def __iter__(self: array[L, n] @ owned) -> SizedIter[ArrayIter[L, n], n]:
        return SizedIter(ArrayIter(self, 0))

    @custom_function(CopyInoutCompiler(), ArrayCopyChecker())
    def copy(self: array[T, n]) -> array[T, n]:
        """Copy an array instance. Will only work if T is a copyable type."""

    @custom_function(ArrayIsBorrowedCompiler(), checker=ArrayIndexChecker())
    def is_borrowed(self: array[L, n], idx: int) -> bool:
        """Checks if an element has been taken out of the array.

        This is the case whenever a non-copyable element is borrowed, or when an element
        is manually taken out of the array via the `take` method.

        .. code-block:: python

            qs = array(qubit() for _ in range(10))
            h(qs[3])
            result("a", qs.is_borrowed(3))  # False
            q = qs.take(3).unwrap()
            result("a", qs.is_borrowed(3))  # True
            qs.put(qubit(), 3).unwrap()
            result("a", qs.is_borrowed(3))  # False
        """

    @custom_function(ArrayGetitemCompiler(), checker=ArrayIndexChecker())
    def take(self: array[L, n], idx: int) -> L:
        """Takes an element out of the array.

        While regular indexing into an array only allows borrowing of elements, `take`
        actually *extracts* the element and transfers ownership to the caller. This
        makes this operation inherently unsafe: elements may no longer be accessed after
        they are taken out. Attempting to do so will result in a runtime panic.

        The complementary `array.put` method may be used to return an element back into
        the array to make it accessible again.

        Panics if the provided index is negative or out of bounds, or if the element has
        already been taken out.

        Also see `array.try_take` for a version of this function that does not panic if
        the element has already been taken out.

        .. code-block:: python

            qs = array(qubit() for _ in range(10))
            h(qs[3])
            q = qs.take(3)
            measure(q)  # We're allowed to deallocate since we own `q`
            # h(qs[3])  # Would panic since qubit 3 has been taken out
            qs.put(qubit(), 3) # Put a fresh qubit back into the array
            h(qs[3])
        """

    @guppy
    @no_type_check
    def try_take(self: array[L, n], idx: int) -> Option[L]:
        """Tries to take an element out of the array.

        While regular indexing into an array only allows borrowing of elements, `take`
        actually *extracts* the element and transfers ownership to the caller. This
        makes this operation inherently unsafe: elements may no longer be accessed after
        they are taken out. Attempting to do so will result in a runtime panic.

        The complementary `array.put` method may be used to return an element back into
        the array to make it accessible again.

        Returns the extracted element or `nothing` if the element has already been taken
        out. Panics if the provided index is negative or out of bounds.

        .. code-block:: python

            qs = array(qubit() for _ in range(10))
            h(qs[3])
            q = qs.try_take(3).unwrap()
            measure(q)  # We're allowed to deallocate since we own `q`
            # h(qs[3])  # Would panic since qubit 3 has been taken out
            qs.put(qubit(), 3)  # Put a fresh qubit back into the array
            h(qs[3])
        """
        if self.is_borrowed(idx):
            return nothing()
        return some(self.take(idx))

    @custom_function(
        ArraySetitemCompiler(elem_first=True), checker=ArrayIndexChecker(expr_index=2)
    )
    def put(self: array[L, n], elem: L @ owned, idx: int) -> None:
        """Puts an element back into the array if it has been taken out previously.

        This is the complement of `array.take`. It may be used to fill the "hole" left
        by `array.take` with a new element.

        Panics if the provided index is negative or out of bounds, or if there is
        already an element at the given index.

        Also see `array.try_put` for a version of this function that does not panic if
        if there is already an element at the given index.

        .. code-block:: python

            qs = array(qubit() for _ in range(10))
            q = qubit()
            # qs.put(q, 3)  # Would panic as there is already a qubit at index 3
            measure(qs.take(3))  # Take it out to make space for the new one
            qs.put(q, 3)
            h(qs[3])
        """

    @guppy
    @no_type_check
    def try_put(self: array[L, n], elem: L @ owned, idx: int) -> Result[None, L]:
        """Tries to put an element back into the array if it has been taken out
        previously.

        This is the complement of `array.take`. It may be used to fill the "hole" left
        by `array.take` with a new element.

        If there is already an element at the given index, then the array will not be
        mutated and the passed replacement element will be returned back in an `err`
        variant. Panics if the provided index is negative or out of bounds.

        .. code-block:: python

            qs = array(qubit() for _ in range(10))
            q = qubit()
            # Is `nothing` since there's a qubit at idx 3
            qs.try_put(q, 3).unwrap_nothing()
            measure(qs.take(3))  # Take it out to make space for the new one
            qs.try_put(q, 3).unwrap()
            h(qs[3])
        """
        if not self.is_borrowed(idx):
            return err(elem)
        self.put(elem, idx)
        return ok(None)

    def __new__(cls, *args: _T) -> builtins.list[_T]:  # type: ignore[no-redef]
        # Runtime array constructor that is used for comptime. We return an actual list
        # in line with the comptime unpacking logic that turns arrays into lists.
        if len(args) == 1 and isinstance(args[0], GeneratorType):
            return list(args[0])
        return [*args]


@guppy.struct
class ArrayIter(Generic[L, n]):
    """Iterator over arrays."""

    xs: array[L, n]
    i: int

    @guppy
    @no_type_check
    def __next__(
        self: ArrayIter[L, n] @ owned,
    ) -> Option[tuple[L, ArrayIter[L, n]]]:
        if self.i < int(n):
            elem = self.xs.take(self.i)
            return some((elem, ArrayIter(self.xs, self.i + 1)))
        _array_discard_all_used(self.xs)
        return nothing()


@custom_function(ArrayDiscardAllUsedCompiler())
def _array_discard_all_used(xs: array[L, n] @ owned) -> None: ...


@custom_function(ArraySwapCompiler())
def array_swap(arr: array[L, n], idx: int, idx2: int) -> None:
    """Swap two elements in an array at indices idx and idx2.

    Exchanges the elements at two indices within the array. This operation
    uses HUGR's native swap operation from the collections.array extension,

    The swap happens in-place. Panics if either index is out of bounds.

    Works with both copyable and linear types (like qubits).

    Args:
        arr: The array to modify
        idx: Index of first element to swap
        idx2: Index of second element to swap

    .. code-block:: python

        arr = array(10, 20, 30, 40)
        array_swap(arr, 0, 3)
        # arr is now [40, 20, 30, 10]
    """


@extend_type(frozenarray_type_def)
class frozenarray(Generic[T, n]):
    """An immutable array of fixed static size."""

    @custom_function(FrozenarrayGetitemCompiler())
    def __getitem__(self: frozenarray[T, n], item: int) -> T: ...  # type: ignore[type-arg]

    @guppy
    @no_type_check
    def __len__(self: frozenarray[T, n]) -> int:
        return n

    @guppy
    @no_type_check
    def __iter__(self: frozenarray[T, n]) -> SizedIter[FrozenarrayIter[T, n], n]:
        return SizedIter(FrozenarrayIter(self, 0))

    @guppy
    @no_type_check
    def mutable_copy(self: frozenarray[T, n]) -> array[T, n]:
        """Creates a mutable copy of this array."""
        return array(x for x in self)


@guppy.struct
class FrozenarrayIter(Generic[T, n]):
    """Iterator for frozenarrays."""

    xs: frozenarray[T, n]  # type: ignore[type-arg]
    i: int

    @guppy
    @no_type_check
    def __next__(
        self: FrozenarrayIter[T, n],
    ) -> Option[tuple[T, FrozenarrayIter[T, n]]]:
        if self.i < int(n):
            return some((self.xs[self.i], FrozenarrayIter(self.xs, self.i + 1)))
        return nothing()
