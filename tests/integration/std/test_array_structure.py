"""Construction, order-preserving transfers, and static split validation."""

from typing import no_type_check

import pytest

from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.lang import comptime, owned
from guppylang.std.num import nat
from guppylang.std.platform import output
from guppylang.std.quantum import measure, qubit, x
from guppylang_internals.error import GuppyError


@guppy
@no_type_check
def _emit[size: nat](values: array[int, size]) -> None:
    if size:
        output("values", values)
    else:
        # The output backend rejects empty arrays.
        output("length", len(values))


@no_type_check
def test_array_structure() -> None:
    # Empty operands, split endpoints/interior, singleton, and asymmetric joins.
    cases = [
        ([], [], 0),
        ([], [8, 9], 0),
        ([4], [], 0),
        ([4], [], 1),
        ([1, 2, 3], [8, 9], 0),
        ([1, 2, 3], [8, 9], 1),
        ([1, 2, 3], [8, 9], 3),
    ]

    @guppy
    def check[n: nat, m: nat](
        xs: array[int, n] @ owned,
        ys: array[int, m] @ owned,
        position: int @ comptime,
    ) -> None:
        _emit(xs.copy().concat(ys))
        _emit(xs.copy().appended(7))
        left, right = xs.split_at(comptime(position))
        _emit(left)
        _emit(right)

    @guppy
    def empty() -> None:
        check(array(), array(), 0)
        check(array(), array(8, 9), 0)
        check(array(4), array(), 0)
        check(array(4), array(), 1)

    @guppy.comptime
    def main() -> None:
        empty()
        for xs, ys, position in cases[4:]:
            check(list(xs), list(ys), position)

    entries = main.emulator(0).coinflip_sim().run()[0].entries
    expected = []
    for xs, ys, position in cases:
        expected.extend(
            ("values", values) if values else ("length", 0)
            for values in [xs + ys, xs + [7], xs[:position], xs[position:]]
        )
    assert entries == expected


@no_type_check
def test_linear_split_rejoin() -> None:
    @guppy
    def main() -> None:
        qs = array(qubit() for _ in range(3))
        x(qs[0])
        x(qs[2])
        left, right = qs.split_at(1)
        joined = left.concat(right).appended(qubit())
        for q in joined:
            output("measurement", measure(q).read())

    entries = main.emulator(4).stabilizer_sim().run()[0].entries
    assert entries == [("measurement", value) for value in [True, False, True, False]]


@no_type_check
def test_invalid_split() -> None:
    @guppy
    def main(xs: array[int, 2] @ owned) -> None:
        xs.split_at(3)

    with pytest.raises(GuppyError, match="Split position 3 is out of bounds"):
        main.compile_function()
