"""Focused tests for checked boolean-array and unsigned-integer conversions."""

from collections.abc import Callable
from typing import no_type_check

import pytest

from guppylang import guppy
from guppylang.emulator import Platform
from guppylang.std.array import array, array_from_nat, array_from_nat_le
from guppylang.std.num import nat
from guppylang.std.platform import output
from guppylang_internals.checker.errors.comptime_errors import ComptimeExprEvalError
from guppylang_internals.error import GuppyError


@no_type_check
def test_bit_conversions(
    validate: Callable[..., None], target_platform: Platform
) -> None:
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

    def program(size: int):
        @guppy
        def main(bits: array[bool, size], high: int, low: int) -> None:
            original = bits.copy()
            # Runtime nat arguments are unsupported; both halves fit in signed int.
            value = (nat(high) << nat(32)) | nat(low)
            output("big", bits.to_nat())
            output("little", bits.to_nat_le())
            big = array_from_nat(value, size).unwrap()
            little = array_from_nat_le(value, size).unwrap()
            if size:
                output("big_bits", big)
                output("little_bits", little)
            else:
                # The output backend rejects empty arrays; check their lengths instead.
                output("big_bits", len(big))
                output("little_bits", len(little))
            output("big_roundtrip", big.to_nat())
            output("little_roundtrip", little.to_nat_le())
            unchanged = True
            for i in range(size):
                unchanged = unchanged and bits[i] == original[i]
            output("unchanged", unchanged)

        return main

    empty, one, narrow, full = [program(size) for size in [0, 1, 63, 64]]

    @guppy
    def main(bits: array[bool, 64], high: int, low: int, size: int) -> None:
        if size == 0:
            empty(array(), high, low)
        elif size == 1:
            one(array(bits[0]), high, low)
        elif size == 63:
            narrow(array(bits[i] for i in range(63)), high, low)
        else:
            full(bits, high, low)

    validate(main.compile_function())
    arguments = [
        {
            "bits": bits + [False] * (64 - size),
            "high": value >> 32,
            "low": value & ((1 << 32) - 1),
            "size": size,
        }
        for size, value, bits in cases
    ]
    results = (
        main.emulator(0, platform=target_platform)
        .coinflip_sim()
        .run_per_shot(arguments)
    )
    for (size, value, bits), shot in zip(cases, results, strict=True):
        assert dict(shot.entries) == {
            "big": value,
            "little": sum(int(bit) << i for i, bit in enumerate(bits)),
            "big_bits": bits if size else 0,
            "little_bits": list(reversed(bits)) if size else 0,
            "big_roundtrip": value,
            "little_roundtrip": value,
            "unchanged": True,
        }, f"Width {size}, value {value}"


@no_type_check
def test_bit_conversion_overflow(
    validate: Callable[..., None], target_platform: Platform
) -> None:
    def program(size: int):
        @guppy
        def main(high: int, low: int) -> None:
            value = (nat(high) << nat(32)) | nat(low)
            output("big_nothing", array_from_nat(value, size).is_nothing())
            output("little_nothing", array_from_nat_le(value, size).is_nothing())

        return main

    empty, one, narrow = [program(size) for size in [0, 1, 63]]

    @guppy
    def main(high: int, low: int, size: int) -> None:
        if size == 0:
            empty(high, low)
        elif size == 1:
            one(high, low)
        else:
            narrow(high, low)

    validate(main.compile_function())
    arguments = [
        {"high": (1 << size) >> 32, "low": (1 << size) & ((1 << 32) - 1), "size": size}
        for size in [0, 1, 63]
    ]
    results = (
        main.emulator(0, platform=target_platform)
        .coinflip_sim()
        .run_per_shot(arguments)
    )
    for shot in results:
        assert shot.entries == [("big_nothing", True), ("little_nothing", True)]


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
