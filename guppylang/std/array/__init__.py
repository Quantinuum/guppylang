from __future__ import annotations

from typing import TYPE_CHECKING, Generic

from guppylang.decorator import guppy
from guppylang.std.builtins import ArrayIter, SizedIter, _array_unsafe_getitem
from guppylang.std.option import Option, nothing, some

if TYPE_CHECKING:
    from guppylang.std.builtins import array, owned

n = guppy.nat_var("n")

L = guppy.type_var("L", copyable=False, droppable=False)
L2 = guppy.type_var("L2", copyable=False, droppable=False)


@guppy.struct
class ArrayZipIter(Generic[L, L2, n]):
    """Zipped iterator over arrays."""

    xs: array[L, n]
    ys: array[L2, n]
    i: int

    @guppy
    def __next__(
        self: ArrayZipIter[L, L2, n] @ owned,
    ) -> Option[tuple[tuple[L, L2], ArrayZipIter[L, L2, n]]]:
        if self.i < int(n):
            x = _array_unsafe_getitem(self.xs, self.i)
            y = _array_unsafe_getitem(self.ys, self.i)
            elem = (x, y)
            return some((elem, ArrayZipIter(self.xs, self.ys, self.i + 1)))
        ArrayIter(self.xs, 0)._assert_all_used()
        ArrayIter(self.ys, 0)._assert_all_used()
        return nothing()


@guppy
def zip(
    a: array[L, n] @ owned, b: array[L2, n] @ owned
) -> SizedIter[ArrayZipIter[L, L2, n], n]:
    """Zip two arrays together into an iterator of tuples.
    Args:
        a: First array.
        b: Second array.
    Returns:
        An iterator of tuples, where each tuple contains elements from the two input
        arrays at the same index.
    """
    return SizedIter(ArrayZipIter(a, b, 0))


@guppy
def enumerate(a: array[L, n] @ owned) -> SizedIter[ArrayZipIter[int, L, n], n]:
    """
    Enumerates the elements of an array, pairing each element with its index.

    Args:
        a: The input array of type `L` with size `n`.

    Returns:
        An iterator that yields tuples,
        where each tuple contains an index (int) and the corresponding element
        from the input array.
    """

    return zip(array(i for i in range(n)), a)
