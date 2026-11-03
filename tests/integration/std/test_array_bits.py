"""Focused tests for checked boolean-array and unsigned-integer conversions."""

from itertools import batched
from typing import no_type_check

import pytest

from guppylang import guppy
from guppylang.std.array import array, array_from_nat, array_from_nat_le
from guppylang.std.num import nat
from guppylang.std.lang import comptime
from guppylang.std.platform import output
from guppylang_internals.checker.errors.comptime_errors import ComptimeExprEvalError
from guppylang_internals.error import GuppyError


@no_type_check
def test_bit_conversions() -> None:
    cases = []
    for size in [0, 1, 63, 64]:
        maximum = (1 << size) - 1
        values = sorted(
            {0, maximum, maximum // 3, 1 if size else 0, 1 << (size - 1) if size else 0}
        )
        cases.extend(
            (size, value, [bool((value >> i) & 1) for i in reversed(range(size))])
            for value in values
        )

    @guppy
    def check[size: nat](bits: array[bool, size], high: int, low: int) -> None:
        # Traced Python integers are signed; halves cover the full nat range.
        value = (nat(high) << nat(32)) | nat(low)
        original = bits.copy()
        output("big", bits.to_nat())
        output("little", bits.to_nat_le())
        big = array_from_nat(value, size).unwrap()
        little = array_from_nat_le(value, size).unwrap()
        if size:
            output("big_bits", big)
            output("little_bits", little)
        else:
            output("big_bits", len(big))
            output("little_bits", len(little))
        output("big_roundtrip", big.to_nat())
        output("little_roundtrip", little.to_nat_le())
        unchanged = True
        for i in range(size):
            unchanged = unchanged and bits[i] == original[i]
        output("unchanged", unchanged)

    @guppy
    def empty() -> None:
        check(array(), 0, 0)

    @guppy.comptime
    def main() -> None:
        for size, value, bits in cases:
            if size:
                check(list(bits), value >> 32, value & ((1 << 32) - 1))
            else:
                empty()

    shot = main.emulator(0).coinflip_sim().run()[0]
    for (size, value, bits), entries in zip(
        cases, batched(shot.entries, 7), strict=True
    ):
        assert dict(entries) == {
            "big": value,
            "little": sum(int(bit) << i for i, bit in enumerate(bits)),
            "big_bits": bits if size else 0,
            "little_bits": list(reversed(bits)) if size else 0,
            "big_roundtrip": value,
            "little_roundtrip": value,
            "unchanged": True,
        }, f"Width {size}, value {value}"


@no_type_check
def test_bit_conversion_overflow() -> None:
    widths = [0, 1, 63]

    @guppy
    def check(high: int, low: int, size: int @ comptime) -> None:
        value = (nat(high) << nat(32)) | nat(low)
        output("big_nothing", array_from_nat(value, comptime(size)).is_nothing())
        output("little_nothing", array_from_nat_le(value, comptime(size)).is_nothing())

    @guppy.comptime
    def main() -> None:
        for size in widths:
            value = 1 << size
            check(value >> 32, value & ((1 << 32) - 1), size)

    shot = main.emulator(0).coinflip_sim().run()[0]
    assert shot.entries == [("big_nothing", True), ("little_nothing", True)] * len(
        widths
    )


@pytest.mark.parametrize(
    "operation", ["to_nat", "to_nat_le", "array_from_nat", "array_from_nat_le"]
)
@no_type_check
def test_bit_conversion_invalid_width(operation: str) -> None:
    if operation.startswith("to_nat"):
        convert = getattr(array, operation)

        @guppy
        def main(bits: array[bool, 65]) -> nat:
            return convert(bits)
    else:
        construct = {
            "array_from_nat": array_from_nat,
            "array_from_nat_le": array_from_nat_le,
        }[operation]

        @guppy
        def main() -> array[bool, 65]:
            return construct(nat(0), 65).unwrap()

    with pytest.raises(
        GuppyError, match="Boolean array bit width must be between 0 and 64"
    ) as error:
        main.compile_function()
    assert isinstance(error.value.error, ComptimeExprEvalError)
