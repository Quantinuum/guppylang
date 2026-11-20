from __future__ import annotations

from typing import no_type_check

from guppylang.decorator import guppy
from guppylang.std.builtins import array

n = guppy.nat_var("n")


@guppy
@no_type_check
def array_eq(a: array[bool, n], b: array[bool, n]) -> bool:
    """Check if two boolean arrays are equal element-wise.

    Args:
        a: First boolean array.
        b: Second boolean array.

    Returns:
        True if all elements are equal, False otherwise.
    """
    for i in range(n):
        if a[i] != b[i]:
            return False
    return True


@guppy
@no_type_check
def array_any(arr: array[bool, n]) -> bool:
    """Check if any element in the boolean array is True.

    Args:
        arr: Boolean array.

    Returns:
        True if at least one element is True, False otherwise.
    """
    for i in range(n):
        if arr[i]:
            return True
    return False


@guppy
@no_type_check
def array_all(arr: array[bool, n]) -> bool:
    """Check if all elements in the boolean array are True.

    Args:
        arr: Boolean array.

    Returns:
        True if all elements are True, False otherwise.
    """
    for i in range(n):
        if not arr[i]:
            return False
    return True


@guppy
@no_type_check
def parity(bits: array[bool, n]) -> bool:
    """Compute the parity of a boolean array.

    Args:
        bits: Boolean array.

    Returns:
        True if the number of True elements is odd, False otherwise.
    """
    out = False
    for i in range(n):
        out ^= bits[i]
    return out


@guppy
@no_type_check
def bitwise_xor(x: array[bool, n], y: array[bool, n]) -> array[bool, n]:
    """Perform bitwise XOR operation on two boolean arrays.

    Args:
        x: First boolean array.
        y: Second boolean array.

    Returns:
        Resultant boolean array after XOR operation.
    """
    return array(x[i] ^ y[i] for i in range(n))


@guppy
@no_type_check
def pack_bits_dlo(ar: array[bool, n]) -> int:
    """Pack bits into an integer assuming decreasing lexicographical order.

    The first element of the array is considered the most significant bit.

    Args:
        ar: Boolean array.

    Returns:
        Integer representation of the packed bits.
    """
    out = 0
    for i in range(n):
        if ar[i]:
            out += 1 << (n - 1 - i)
    return out
