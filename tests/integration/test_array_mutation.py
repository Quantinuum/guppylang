"""In-place updates and permutations preserve complete arrays and linear elements."""

from typing import no_type_check

import pytest

from guppylang import guppy
from guppylang.emulator import EmulatorError
from guppylang.std.array import array, array_swap
from guppylang.std.num import nat
from guppylang.std.platform import output
from guppylang.std.quantum import measure, qubit, x


@guppy
@no_type_check
def _emit[n: nat](values: array[int, n]) -> None:
    if n:
        output("values", values)
    else:
        # The output backend rejects empty arrays.
        output("length", len(values))


@no_type_check
def test_array_mutations() -> None:
    cases = [[], [7], [1, 2, 3, 4], [3, 1, 4, 2, 5]]

    @guppy
    def check[n: nat](xs: array[int, n]) -> None:
        if n:
            swapped = xs.copy()
            swapped.swap(0, n - 1)
            _emit(swapped)
            swapped.swap(0, 0)
            _emit(swapped)
            primitive = xs.copy()
            array_swap(primitive, 0, n - 1)
            _emit(primitive)
            array_swap(primitive, 0, 0)
            _emit(primitive)
        filled = xs.copy()
        filled.fill(-7)
        _emit(filled)
        reversed_values = xs.copy()
        reversed_values.reverse_in_place()
        _emit(reversed_values)
        for amount in range(2 * n + 2):
            left = xs.copy()
            left.rotate_left_in_place(amount)
            _emit(left)
            right = xs.copy()
            right.rotate_right_in_place(amount)
            _emit(right)
        _emit(xs)

    @guppy
    def empty() -> None:
        check(array())

    @guppy
    def flags() -> None:
        xs = array(False, True)
        xs.fill(True)
        output("flags", xs)

    @guppy.comptime
    def main() -> None:
        empty()
        for values in cases[1:]:
            check(list(values))
        flags()

    expected = []
    for values in cases:
        size = len(values)
        if values:
            swapped = values.copy()
            swapped[0], swapped[-1] = swapped[-1], swapped[0]
            # Each swap API exchanges endpoints, then swaps an index with itself.
            # The second call leaves the endpoint-swapped result unchanged.
            expected.extend([("values", swapped)] * 4)

        # The helper emits fill, reverse, paired left/right rotations, then xs.
        results = [[-7] * size, list(reversed(values))]
        # Cover every offset, two complete turns, and one step beyond them.
        for amount in range(2 * size + 2):
            offset = amount % size if values else 0
            # Left moves the prefix to the end; right moves the suffix to the front.
            left = values[offset:] + values[:offset]
            right_start = size - offset
            right = values[right_start:] + values[:right_start]
            results.extend([left, right])
        results.append(values)  # All operations acted on copies; xs is unchanged.
        expected.extend(
            ("values", result) if result else ("length", 0) for result in results
        )
    expected.append(("flags", [True, True]))
    assert main.emulator(0).coinflip_sim().run()[0].entries == expected


@no_type_check
def test_linear_permutations() -> None:
    @guppy
    def main() -> None:
        # An asymmetric preparation distinguishes the composed permutation.
        qs = array(qubit() for _ in range(5))  # 00000
        x(qs[0])  # 10000
        x(qs[1])  # 11000
        qs.swap(0, 4)  # 01001
        qs.swap(2, 2)  # 01001
        array_swap(qs, 1, 3)  # 00011
        array_swap(qs, 2, 2)  # 00011
        qs.reverse_in_place()  # 11000
        qs.rotate_left_in_place(7)  # 00011
        qs.rotate_right_in_place(6)  # 10001
        for q in qs:
            output("measurement", measure(q).read())

    assert main.emulator(5).stabilizer_sim().run()[0].entries == [
        ("measurement", value) for value in [True, False, False, False, True]
    ]


@no_type_check
def test_rotation_invalid_amount() -> None:
    @guppy
    def main(amount: int, right: bool) -> None:
        xs = array(1, 2, 3)
        if right:
            xs.rotate_right_in_place(amount)
        else:
            xs.rotate_left_in_place(amount)
        output("values", xs)

    emulator = main.emulator(0).coinflip_sim()
    for right in [False, True]:
        with pytest.raises(EmulatorError, match="Rotation amount must be nonnegative"):
            emulator.run(amount=-1, right=right)


@no_type_check
def test_swap_invalid_index() -> None:
    @guppy
    def main(first: int, second: int, method: bool) -> None:
        xs = array(1, 2)
        if method:
            xs.swap(first, second)
        else:
            array_swap(xs, first, second)
        output("values", xs)

    emulator = main.emulator(0).coinflip_sim()
    for first, second in [(-1, 0), (0, -1), (2, 0), (0, 2), (2, 2)]:
        for method in [False, True]:
            with pytest.raises(EmulatorError, match="Array swap failed"):
                emulator.run(first=first, second=second, method=method)
