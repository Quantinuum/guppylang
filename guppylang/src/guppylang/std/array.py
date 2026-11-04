"""Utilities for fixed-size arrays, denoted `array[T, n]`, for element type `T` and
compile-time constant size `n`.

See `frozenarray[T, n]` for an immutable version of the `array[T, n]` type.
"""

# mypy: disable-error-code="empty-body, misc, override, valid-type, no-untyped-def"

from __future__ import annotations

import builtins
from types import GeneratorType
from typing import TYPE_CHECKING, Self, no_type_check

from guppylang_internals.decorator import custom_function, extend_type, hugr_op
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
from guppylang_internals.std._internal.util import external_op, type_arg
from guppylang_internals.tys import Effect
from guppylang_internals.tys.builtin import array_type_def, frozenarray_type_def
from guppylang_internals.tys.ty import UnitaryFlags
from hugr import tys as ht
from hugr.std.collections.borrow_array import EXTENSION

from guppylang import guppy
from guppylang.std.err import Result, err, ok
from guppylang.std.iter import SizedIter
from guppylang.std.lang import Copy, Drop, comptime
from guppylang.std.mem import mem_swap
from guppylang.std.num import nat
from guppylang.std.option import Option, nothing, some

if TYPE_CHECKING:
    from guppylang.std.lang import owned


# This equality bound is local until collection-wide interfaces are justified.
@guppy.protocol
class _ArrayEquality:
    @guppy.require
    def __eq__(self: Self, other: Self) -> bool: ...


def _check_array_index(index: int, size: int) -> None:
    """Validate a static array index before generating access code."""
    if not 0 <= index < size:
        msg = f"Array index {index} is out of bounds for array of size {size}"
        raise ValueError(msg)


def _check_bit_width(size: int) -> None:
    """Validate the static width before generating any conversion code."""
    # The comptime evaluator wraps Python exceptions in a source-located GuppyError.
    if not 0 <= size <= 64:
        msg = "Boolean array bit width must be between 0 and 64"
        raise ValueError(msg)


@extend_type(
    array_type_def,
    # Instruct the decorator to return the original class instead of the Guppy array
    # definition. This allows us to customise the runtime behaviour of arrays in
    # comptime to behave like lists.
    return_class=True,
)
class array[T, n: nat](builtins.list[T]):
    """Sequence of homogeneous values with statically known fixed length."""

    @custom_function(
        ArrayGetitemCompiler(),
        checker=ArrayIndexChecker(),
        effects=(),  # Preserving legacy behaviour for linear arrays to support
        # optimization, https://github.com/Quantinuum/guppylang/issues/2122.
        # For classical arrays, ArrayIndexChecker adds effects
        # for the (separately compiled) unwrap.
    )
    def __getitem__(self, idx: int) -> T: ...

    @custom_function(
        ArraySetitemCompiler(),
        checker=ArrayIndexChecker(),
        effects=(),  # Preserving legacy behaviour for linear arrays to support
        # optimization, https://github.com/Quantinuum/guppylang/issues/2122.
        # For classical arrays, ArrayIndexChecker adds effects
        # for the (separately compiled) unwrap.
    )
    def __setitem__(self, idx: int, value: T @ owned) -> None: ...

    @guppy
    @no_type_check
    def __len__(self) -> int:
        return n

    @custom_function(
        NewArrayCompiler(),
        checker=NewArrayChecker(),
        higher_order_value=False,
        unitary_flags=UnitaryFlags.Dagger,
        effects=(),
    )
    def __new__(): ...

    # `__new__` will be overwritten below to provide actual runtime behaviour for
    # comptime. We still need to hold on to a reference to the Guppy function so
    # `@extend_type` can find it
    __new_guppy__ = __new__

    @guppy
    @no_type_check
    def __iter__[L, n: nat](self: array[L, n] @ owned) -> SizedIter[ArrayIter[L, n], n]:
        return SizedIter(ArrayIter(self, 0))

    @custom_function(
        CopyInoutCompiler(),
        checker=ArrayCopyChecker(),
        unitary_flags=UnitaryFlags.Dagger,
        effects=(),
    )
    def copy[T: Copy, n: nat](self: array[T, n]) -> array[T, n]:
        """Copy an array instance. Will only work if T is a copyable type."""

    @custom_function(
        ArrayIsBorrowedCompiler(),
        checker=ArrayIndexChecker(),
        unitary_flags=UnitaryFlags.Dagger,
        effects=[Effect.PANIC],  # If index out-of-bounds
    )
    def is_borrowed(self, idx: int) -> bool:
        """Checks if an element has been taken out of the array.

        This is the case whenever a non-copyable element is borrowed, or when an element
        is manually taken out of the array via the `take` method.

        .. code-block:: python

            qs = array(qubit() for _ in range(10))
            h(qs[3])
            output("a", qs.is_borrowed(3))  # False
            q = qs.take(3).unwrap()
            output("a", qs.is_borrowed(3))  # True
            qs.put(qubit(), 3).unwrap()
            output("a", qs.is_borrowed(3))  # False
        """

    @custom_function(
        ArrayGetitemCompiler(),
        checker=ArrayIndexChecker(),
        effects=(),  # Panics if element already taken, or index out-of-bounds,
        # but we record only for copyable elements (to match __getitem__),
        # done in ArrayIndexChecker (https://github.com/Quantinuum/guppylang/issues/2122).
    )
    def take(self, idx: int) -> T:
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
    def try_take(self, idx: int) -> Option[T]:
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
        ArraySetitemCompiler(elem_first=True),
        checker=ArrayIndexChecker(expr_index=2),
        effects=(),  # Panics if element not taken, or index out-of-bounds,
        # but we record only for copyable elements (to match __getitem__),
        # done in ArrayIndexChecker (https://github.com/Quantinuum/guppylang/issues/2122).
    )
    def put(self, elem: T @ owned, idx: int) -> None:
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
    def try_put(self, elem: T @ owned, idx: int) -> Result[None, T]:
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

    @custom_function(ArrayDiscardAllUsedCompiler(), effects=[Effect.PANIC])
    def discard_all_taken[L, n: nat](self: array[L, n] @ owned) -> None:
        """Discards array assuming that all elements have been taken out, and panics if
        that is not the case.

        .. code-block:: python

            qs = array(qubit() for _ in range(2))
            discard(qs.take(0))
            discard(qs.take(1))
            # qs.put(qubit(), 1) # Would make the call below panic
            qs.discard_all_taken() # Succeeds since all qubits have been taken out
        """

    @guppy
    @no_type_check
    def try_discard_all_taken[L, n: nat](
        self: array[L, n] @ owned,
    ) -> Result[None, array[L, n]]:
        """Similar to `discard_all_taken`, but instead of panicking returns the
        unmodified array when not all elements have been taken out.

        .. code-block:: python

            qs = array(qubit() for _ in range(2))
            discard(qs.take(0))
            # Does not panic, even though not all elements have been taken out.
            qs = qs.try_discard_all_taken()
        """
        for i in range(n):
            if not self.is_borrowed(i):
                return err(self)
        self.discard_all_taken()
        return ok(None)

    def __new__(cls, *args: T) -> builtins.list[T]:  # type: ignore[no-redef]
        # Runtime array constructor that is used for comptime. We return an actual list
        # in line with the comptime unpacking logic that turns arrays into lists.
        if len(args) == 1 and isinstance(args[0], GeneratorType):
            return list(args[0])
        return [*args]

    @guppy
    @no_type_check
    def reverse_in_place(self) -> None:
        """Reverse array elements in-place.

        .. code-block:: python

            qs = array(qubit() for _ in range(2))
            qs.reverse_in_place()
        """
        for i in range(n // 2):
            mem_swap(self[i], self[n - i - 1])

    @guppy
    @no_type_check
    def get[T: Copy, n: nat](self: array[T, n], index: int) -> Option[T]:
        """Return a copy at index, or nothing for negative/out-of-range indices.

        Borrows the array. Requires Copy; takes O(1) time and auxiliary space.

        .. code-block:: python

            values = array(3, 7)
            value = values.get(1)  # some(7)
            missing = values.get(-1)  # nothing
        """
        if index < 0 or index >= n:
            return nothing()
        return some(self[index])

    @guppy
    @no_type_check
    def get_static[T: Copy, n: nat](self: array[T, n], index: nat @ comptime) -> T:
        """Return a copy at a compile-time index, rejecting out-of-bounds indices.

        Borrows the array and requires Copy. The index must satisfy 0 <= index < n;
        empty arrays have no valid index. Takes O(1) time and auxiliary space.

        .. code-block:: python

            values = array(3, 7)
            value = values.get_static(1)  # 7
        """
        comptime(_check_array_index(index, n))
        return self[int(index)]

    @guppy
    @no_type_check
    def first[T: Copy, n: nat](self: array[T, n]) -> T:
        """Return a copy of the first element, rejecting empty arrays at compile time.

        Borrows the array. Requires Copy; O(1) time and auxiliary space.
        """
        return self.get_static(0)

    @guppy
    @no_type_check
    def last[T: Copy, n: nat](self: array[T, n]) -> T:
        """Return a copy of the last element, rejecting empty arrays at compile time.

        Borrows the array. Requires Copy; O(1) time and auxiliary space.
        """
        return self.get_static(comptime(n - 1))

    @guppy
    @no_type_check
    def is_empty(self) -> bool:
        """Return whether the static length is zero, borrowing the array.

        Takes O(1) time and auxiliary space; supports linear elements.
        """
        return n == 0

    @guppy
    @no_type_check
    def __eq__[T: _ArrayEquality, n: nat, m: nat](
        self: array[T, n], other: array[T, m]
    ) -> bool:
        """Compare borrowed arrays using element equality in index order.

        Different lengths return False immediately; two empty arrays are equal.
        Stops at the first mismatch. Supports linear elements with borrowed
        equality. O(n) worst-case time excluding equality costs, O(1) auxiliary
        space.
        """
        if n != m:  # type: ignore[name-defined]
            return False
        for i in range(n):  # noqa: SIM110 - Guppy has no builtin all yet.
            if not self[i].__eq__(other[i]):
                return False
        return True

    @guppy
    @no_type_check
    def __ne__[T: _ArrayEquality, n: nat, m: nat](
        self: array[T, n], other: array[T, m]
    ) -> bool:
        """Return the negation of array equality, borrowing both arrays.

        Different lengths are unequal; two empty arrays are not unequal.
        Supports linear elements with borrowed equality, stopping at the first
        mismatch. O(n) worst-case time excluding equality costs and O(1)
        auxiliary space.
        """
        return not self.__eq__(other)

    @guppy
    @no_type_check
    def contains[T: _ArrayEquality, n: nat](self: array[T, n], value: T) -> bool:
        """Return whether value occurs, or False for an empty array.

        Borrows the array and value, supporting linear elements with borrowed
        equality. Scans in index order, stopping at the first match. O(n)
        worst-case time excluding equality costs, O(1) auxiliary space.
        """
        for i in range(n):  # noqa: SIM110 - Guppy has no builtin any yet.
            if self[i].__eq__(value):
                return True
        return False

    @guppy
    @no_type_check
    def count[T: _ArrayEquality, n: nat](self: array[T, n], value: T) -> int:
        """Count occurrences of value, returning zero for an empty array.

        Borrows the array and value, supporting linear elements with borrowed
        equality. Compares each element once in index order. O(n) time excluding
        equality costs and O(1) auxiliary space.
        """
        total = 0
        for i in range(n):
            if self[i].__eq__(value):
                total += 1
        return total

    # Borrowed indexing allows early exit without consuming linear elements.
    # An iterable abstraction must define ownership of unconsumed elements
    # before it can provide equivalent short-circuit reductions.
    @guppy
    @no_type_check
    def any[n: nat](self: array[bool, n]) -> bool:
        """Return whether any element is true, or ``False`` for an empty array.

        Borrows the array without modifying it. Scans in index order and stops
        at the first true element. Takes O(n) time in the worst case and O(1)
        auxiliary space. Panics if an accessed element is missing.

        .. code-block:: python

            any_true = array(False, True).any()  # True
        """
        for i in range(n):  # noqa: SIM110 - Guppy has no builtin any yet.
            if self[i]:
                return True
        return False

    @guppy
    @no_type_check
    def all[n: nat](self: array[bool, n]) -> bool:
        """Return whether all elements are true, or ``True`` for an empty array.

        Borrows the array without modifying it. Scans in index order and stops
        at the first false element. Takes O(n) time in the worst case and O(1)
        auxiliary space. Panics if an accessed element is missing.

        .. code-block:: python

            all_true = array(True, False).all()  # False
        """
        for i in range(n):  # noqa: SIM110 - Guppy has no builtin all yet.
            if not self[i]:
                return False
        return True

    @guppy
    @no_type_check
    def count_true[n: nat](self: array[bool, n]) -> int:
        """Count true elements, returning zero for an empty array.

        Borrows the array without modifying it. A single scan takes O(n) time
        and O(1) auxiliary space. Panics if an element is missing.

        .. code-block:: python

            count = array(True, False, True).count_true()  # 2
        """
        count = 0
        for i in range(n):
            count += int(self[i])
        return count

    @guppy
    @no_type_check
    def parity[n: nat](self: array[bool, n]) -> bool:
        """Return the XOR of all elements, or ``False`` for an empty array.

        The result is true exactly when an odd number of elements are true.
        Borrows the array without modifying it. A single scan takes O(n) time
        and O(1) auxiliary space. Panics if an element is missing.

        .. code-block:: python

            from guppylang.std.quantum import measure_array, qubit, x

            qs = array(qubit() for _ in range(3))
            x(qs[0])
            outcomes = array(m.read() for m in measure_array(qs))
            odd_parity = outcomes.parity()  # True
        """
        parity = False
        for i in range(n):
            parity ^= self[i]
        return parity

    # These operations borrow both inputs. A shared zip/map/fold abstraction
    # must preserve borrowing and equal static lengths to implement this API.
    @guppy
    @no_type_check
    def bitwise_and[n: nat](
        self: array[bool, n], other: array[bool, n]
    ) -> array[bool, n]:
        """Return the elementwise AND of two boolean arrays of equal length.

        Borrows both inputs without modifying them and returns a new array.
        Empty inputs produce an empty array. Takes O(n) time and O(1)
        auxiliary space, excluding the O(n) output array.
        """
        return array(self[i] & other[i] for i in range(n))

    @guppy
    @no_type_check
    def bitwise_or[n: nat](
        self: array[bool, n], other: array[bool, n]
    ) -> array[bool, n]:
        """Return the elementwise OR of two boolean arrays of equal length.

        Borrows both inputs without modifying them and returns a new array.
        Empty inputs produce an empty array. Takes O(n) time and O(1)
        auxiliary space, excluding the O(n) output array.
        """
        return array(self[i] | other[i] for i in range(n))

    @guppy
    @no_type_check
    def bitwise_xor[n: nat](
        self: array[bool, n], other: array[bool, n]
    ) -> array[bool, n]:
        """Return the elementwise XOR of two boolean arrays of equal length.

        Borrows both inputs without modifying them and returns a new array.
        Empty inputs produce an empty array. Takes O(n) time and O(1)
        auxiliary space, excluding the O(n) output array.

        .. code-block:: python

            expected = array(True, False, True)
            observed = array(True, True, False)
            differences = observed.bitwise_xor(expected)  # [False, True, True]
        """
        return array(self[i] ^ other[i] for i in range(n))

    @guppy
    @no_type_check
    def bitwise_not[n: nat](self: array[bool, n]) -> array[bool, n]:
        """Return a new boolean array with every element negated.

        Borrows the input without modifying it. An empty input produces an
        empty array. Takes O(n) time and O(1) auxiliary space, excluding the
        O(n) output array.
        """
        return array(not self[i] for i in range(n))

    @guppy
    @no_type_check
    def dot[n: nat](self: array[bool, n], other: array[bool, n]) -> bool:
        """Return the GF(2) scalar product of equal-length boolean arrays.

        Computes the XOR of pairwise ANDs, or ``False`` for empty arrays.
        Borrows both inputs without modifying them. A single scan takes
        O(n) time and O(1) auxiliary space without an intermediate array.

        .. code-block:: python

            outcomes = array(True, False, True)
            mask = array(True, False, False)
            selected_parity = outcomes.dot(mask)  # True
        """
        parity = False
        for i in range(n):
            parity ^= self[i] & other[i]
        return parity

    @guppy
    @no_type_check
    def __and__[n: nat](self: array[bool, n], other: array[bool, n]) -> array[bool, n]:
        """Implement ``xs & ys`` using `bitwise_and`."""
        return self.bitwise_and(other)

    @guppy
    @no_type_check
    def __or__[n: nat](self: array[bool, n], other: array[bool, n]) -> array[bool, n]:
        """Implement ``xs | ys`` using `bitwise_or`."""
        return self.bitwise_or(other)

    @guppy
    @no_type_check
    def __xor__[n: nat](self: array[bool, n], other: array[bool, n]) -> array[bool, n]:
        """Implement ``xs ^ ys`` using `bitwise_xor`."""
        return self.bitwise_xor(other)

    @guppy
    @no_type_check
    def __invert__[n: nat](self: array[bool, n]) -> array[bool, n]:
        """Implement ``~xs`` using `bitwise_not`."""
        return self.bitwise_not()

    @guppy
    @no_type_check
    def __matmul__[n: nat](self: array[bool, n], other: array[bool, n]) -> bool:
        """Implement ``xs @ ys`` using `dot`."""
        return self.dot(other)

    @guppy
    @no_type_check
    def __nat__[n: nat](self: array[bool, n]) -> nat:
        """Implement ``nat(xs)`` using `to_nat`, most significant bit first."""
        return self.to_nat()

    @guppy
    @no_type_check
    def to_nat[n: nat](self: array[bool, n]) -> nat:
        """Convert a boolean array to an unsigned integer, most significant bit first.

        Index 0 is the most significant bit. An empty array represents zero.
        The static length must be between 0 and 64; other lengths are rejected
        during compilation. Borrows the input without modifying it.

        A left-to-right shift-and-OR scan takes O(n) time and O(1) auxiliary
        space. Each shift is by one bit, including at width 64.

        .. code-block:: python

            bits = array(True, False, False)
            value = bits.to_nat()  # nat(4)
        """
        comptime(_check_bit_width(n))
        value = nat(0)
        for i in range(n):
            value = (value << nat(1)) | nat(self[i])
        return value

    @guppy
    @no_type_check
    def to_nat_le[n: nat](self: array[bool, n]) -> nat:
        """Convert a boolean array to an unsigned integer, least significant bit first.

        Index 0 is the least significant bit. An empty array represents zero.
        The static length must be between 0 and 64; other lengths are rejected
        during compilation. Borrows the input without modifying it.

        A right-to-left shift-and-OR scan takes O(n) time and O(1) auxiliary
        space. Each shift is by one bit, including at width 64.

        .. code-block:: python

            bits = array(True, False, False)
            value = bits.to_nat_le()  # nat(1)
        """
        comptime(_check_bit_width(n))
        value = nat(0)
        for i in range(n):
            value = (value << nat(1)) | nat(self[n - i - 1])
        return value


@guppy
@no_type_check
def array_from_nat(value: nat, size: nat @ comptime) -> Option[array[bool, size]]:
    """Convert an unsigned integer to a boolean array, most significant bit first.

    Index 0 is the most significant bit. The compile-time size must be between
    0 and 64; other sizes are rejected during compilation. Returns ``some(array)``
    if the value fits in the requested size, or ``nothing`` otherwise. Size zero
    accepts only zero.

    Extracting each bit takes O(size) time and O(1) auxiliary space, excluding
    the O(size) output array. Runtime shifts are at most 63 bits.

    .. code-block:: python

        bits = array_from_nat(nat(4), 3).unwrap()  # [True, False, False]
    """
    comptime(_check_bit_width(size))
    maximum: nat = comptime((1 << size) - 1)
    if value > maximum:
        return nothing()
    return some(array(bool((value >> nat(size - i - 1)) & nat(1)) for i in range(size)))


@guppy
@no_type_check
def array_from_nat_le(value: nat, size: nat @ comptime) -> Option[array[bool, size]]:
    """Convert an unsigned integer to a boolean array, least significant bit first.

    Index 0 is the least significant bit. The compile-time size must be between
    0 and 64; other sizes are rejected during compilation. Returns ``some(array)``
    if the value fits in the requested size, or ``nothing`` otherwise. Size zero
    accepts only zero.

    Extracting each bit takes O(size) time and O(1) auxiliary space, excluding
    the O(size) output array. Runtime shifts are at most 63 bits.

    .. code-block:: python

        bits = array_from_nat_le(nat(4), 3).unwrap()  # [False, False, True]
    """
    comptime(_check_bit_width(size))
    maximum: nat = comptime((1 << size) - 1)
    if value > maximum:
        return nothing()
    return some(array(bool((value >> nat(i)) & nat(1)) for i in range(size)))


@hugr_op(
    external_op(
        "new_all_borrowed",
        [ht.VariableArg(idx=1, param=ht.BoundedNatParam()), type_arg(0)],
        EXTENSION,
    ),
    effects=[],
)
def empty_array[T, n: nat]() -> array[T, n]:
    """Construct an array with all elements borrowed.

    Elements must be added with `array.put` before they can be accessed. Since no
    elements are present initially, `array.discard_all_taken` may be called immediately.
    """


@guppy.struct
class ArrayIter[L, n: nat]:
    """Iterator over arrays."""

    _xs: array[L, n]
    _i: int

    @guppy
    @no_type_check
    def __next__(
        self: Self @ owned,
    ) -> Option[tuple[L, Self]]:
        if self._i < int(n):
            elem = self._xs.take(self._i)
            self._i += 1
            return some((elem, self))
        self._xs.discard_all_taken()
        return nothing()


@custom_function(ArraySwapCompiler(), effects=[Effect.PANIC])
def array_swap[L, n: nat](arr: array[L, n], idx: int, idx2: int) -> None:
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
class frozenarray[T, n: nat]:
    """An immutable array of fixed static size."""

    # Panics on out-of-range.
    @custom_function(FrozenarrayGetitemCompiler(), effects=[Effect.PANIC])
    def __getitem__(self, item: int) -> T: ...

    @guppy
    @no_type_check
    def __len__(self) -> int:
        return n

    @guppy
    @no_type_check
    def __iter__(self) -> SizedIter[FrozenarrayIter[T, n], n]:
        return SizedIter(FrozenarrayIter(self, 0))

    @guppy
    @no_type_check
    def mutable_copy(self) -> array[T, n]:
        """Creates a mutable copy of this array."""
        return array(x for x in self)


@guppy.struct
class FrozenarrayIter[T: (Copy, Drop), n: nat]:
    """Iterator for frozenarrays."""

    _xs: frozenarray[T, n]
    _i: int

    @guppy
    @no_type_check
    def __next__(
        self: Self @ owned,
    ) -> Option[tuple[T, Self]]:
        if self._i < int(n):
            elem = self._xs[self._i]
            self._i += 1
            return some((elem, self))
        return nothing()
