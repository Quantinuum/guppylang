"""Subarray copying and consuming shape transformations."""

from typing import no_type_check

import pytest

from guppylang import guppy
from guppylang.emulator import EmulatorError
from guppylang.std.array import array
from guppylang.std.lang import comptime, owned
from guppylang.std.num import nat
from guppylang.std.platform import output
from guppylang.std.quantum import measure, qubit, x
from guppylang_internals.error import GuppyError


@guppy
@no_type_check
def _emit[n: nat](values: array[int, n]) -> None:
    if n:
        output("values", values)
    else:
        # The output backend rejects empty arrays.
        output("length", len(values))


@no_type_check
def test_subarray() -> None:
    cases = [(0, 0), (0, 1), (1, 2), (0, 4), (4, 0)]

    @guppy
    def check(xs: array[int, 4], start: int, size: int @ comptime) -> None:
        _emit(xs.subarray(start, comptime(size)))
        output("retained", xs)

    @guppy
    def empty() -> None:
        xs: array[int, 0] = array()
        _emit(xs.subarray(0, 0))

    @guppy.comptime
    def main() -> None:
        empty()
        for start, size in cases:
            check([1, 2, 3, 4], start, size)

    entries = main.emulator(0).coinflip_sim().run()[0].entries
    expected = [("length", 0)]
    for start, size in cases:
        values = [1, 2, 3, 4][start : start + size]
        expected.extend(
            [
                ("values", values) if values else ("length", 0),
                ("retained", [1, 2, 3, 4]),
            ]
        )
    assert entries == expected


@no_type_check
def test_pairing_and_shapes() -> None:
    @guppy
    def check[n: nat](xs: array[int, n] @ owned) -> None:
        flags = array(i % 2 == 0 for i in range(n))
        pairs = xs.zip(flags)
        for pair in pairs:
            number, flag = pair
            output("number", number)
            output("flag", flag)

    @guppy
    def main() -> None:
        check(array())
        check(array(7))
        check(array(3, 1, 4))
        # Test unzip independently of zip.
        numbers, flags = array((4, False), (9, True)).unzip()
        _emit(numbers)
        output("flags", flags)
        empty_pairs: array[tuple[int, bool], 0] = array()
        empty_numbers, empty_flags = empty_pairs.unzip()
        _emit(empty_numbers)
        output("empty_flags", len(empty_flags))
        _emit(array(array(1, 2), array(3, 4)).flatten())
        empty_rows: array[array[int, 2], 0] = array()
        _emit(empty_rows.flatten())
        row: array[int, 0] = array()
        _emit(array(row.copy(), row).flatten())
        for row in array(1, 2, 3, 4).chunks(2):
            _emit(row)
        for row in array(7).chunks(1):
            _emit(row)
        for row in array(8, 9).chunks(2):
            _emit(row)
        empty_values: array[int, 0] = array()
        output("empty_chunks", len(empty_values.chunks(2)))

    entries = main.emulator(0).coinflip_sim().run()[0].entries
    assert entries == [
        ("number", 7),
        ("flag", True),
        ("number", 3),
        ("flag", True),
        ("number", 1),
        ("flag", False),
        ("number", 4),
        ("flag", True),
        ("values", [4, 9]),
        ("flags", [False, True]),
        ("length", 0),
        ("empty_flags", 0),
        ("values", [1, 2, 3, 4]),
        ("length", 0),
        ("length", 0),
        ("values", [1, 2]),
        ("values", [3, 4]),
        ("values", [7]),
        ("values", [8, 9]),
        ("empty_chunks", 0),
    ]


@no_type_check
def test_linear_shapes() -> None:
    @guppy
    def main() -> None:
        qs = array(qubit() for _ in range(4))
        x(qs[0])
        x(qs[3])
        pairs = qs.zip(array(0, 1, 2, 3))
        recovered, labels = pairs.unzip()
        output("labels", labels)
        for q in recovered.chunks(2).flatten():
            output("measurement", measure(q).read())

    entries = main.emulator(4).stabilizer_sim().run()[0].entries
    assert entries == [("labels", [0, 1, 2, 3])] + [
        ("measurement", value) for value in [True, False, False, True]
    ]


@no_type_check
def test_subarray_invalid_start() -> None:
    @guppy
    def main(start: int) -> None:
        _emit(array(1, 2).subarray(start, 1))

    emulator = main.emulator(0).coinflip_sim()
    for start in [-1, 2, 3]:
        with pytest.raises(EmulatorError, match="Subarray bounds are out of range"):
            emulator.run(start=start)


@pytest.mark.parametrize("size", [0, 3], ids=["zero", "non-divisor"])
@no_type_check
def test_invalid_chunk_size(size: int) -> None:
    @guppy
    def main(xs: array[int, 4] @ owned) -> None:
        xs.chunks(size)

    with pytest.raises(GuppyError, match="Chunk size must be positive and divide"):
        main.compile_function()


@no_type_check
def test_invalid_subarray_size() -> None:
    @guppy
    def main(xs: array[int, 2]) -> None:
        xs.subarray(0, 3)

    with pytest.raises(GuppyError, match="Subarray size must be between"):
        main.compile_function()
