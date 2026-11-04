"""Safe access and structurally constrained value comparisons."""

from typing import Self, no_type_check

import pytest

from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.lang import comptime
from guppylang.std.num import nat
from guppylang.std.option import Option
from guppylang.std.platform import output
from guppylang_internals.error import GuppyError
from guppylang.std.quantum import discard, qubit


@guppy
@no_type_check
def _emit_option(value: Option[int]) -> None:
    output("some", value.is_some())
    if value.is_some():
        output("value", value.unwrap())


@no_type_check
def test_array_queries() -> None:
    # Named cases cover each access boundary and both equal/unequal arrays,
    # with single, repeated, and absent search values without a Cartesian matrix.
    cases = [
        ("empty", (), (), -1, 2),
        ("singleton-match", (2,), (2,), 0, 2),
        ("singleton-miss", (2,), (3,), 1, 9),
        ("negative", (0, 1, 2), (0, 1, 2), -1, 2),
        ("first", (0, 1, 2), (0, 1, 9), 0, 0),
        ("last", (0, 1, 2), (0, 1, 2), 2, 9),
        ("past-end", (0, 1, 2), (0, 1, 2), 3, -1),
        ("repeated", (2, 2, 2), (2, 2, 2), 1, 2),
    ]

    @guppy
    def check[size: nat](
        xs: array[int, size], ys: array[int, size], index: int, value: int
    ) -> None:
        _emit_option(xs.get(index))
        output("empty", xs.is_empty())
        output("equal", xs == ys)
        output("unequal", xs != ys)
        output("contains", xs.contains(value))
        output("count", xs.count(value))
        other = array(0 for _ in range(comptime(size + 1)))
        output("different_length_equal", xs == other)
        output("different_length_unequal", xs != other)
        if size:
            output("retained", xs)
            output("other_retained", ys)

    @guppy
    def endpoints[size: nat](xs: array[int, size]) -> None:
        output("first", xs.first())
        output("last", xs.last())
        output("static", xs.get_static(0))

    @guppy
    def empty(index: int, value: int) -> None:
        check(array(), array(), index, value)

    @guppy.comptime
    def main() -> None:
        for _, xs, ys, index, value in cases:
            if xs:
                check(list(xs), list(ys), index, value)
                endpoints(list(xs))
            else:
                empty(index, value)

    shot = main.emulator(0).coinflip_sim().run()[0]
    entries = iter(shot.entries)
    for name, xs, ys, index, value in cases:
        size = len(xs)
        selected = [
            xs[index] if 0 <= index < size else None,
        ]
        expected = []
        for item in selected:
            expected.append(("some", item is not None))
            if item is not None:
                expected.append(("value", item))
        expected.extend(
            [
                ("empty", not xs),
                ("equal", xs == ys),
                ("unequal", xs != ys),
                ("contains", value in xs),
                ("count", xs.count(value)),
                ("different_length_equal", False),
                ("different_length_unequal", True),
            ]
        )
        if size:
            expected.extend([("retained", list(xs)), ("other_retained", list(ys))])
            expected.extend([("first", xs[0]), ("last", xs[-1]), ("static", xs[0])])
        assert [next(entries) for _ in expected] == expected, name
    assert next(entries, None) is None


@no_type_check
def test_custom_linear_equality() -> None:
    @guppy.struct
    class Record:
        q: qubit
        key: int

        @guppy
        def __eq__(self: Self, other: Self) -> bool:
            output("compare", self.key)
            return self.key == other.key

    @guppy
    def main() -> None:
        xs = array(Record(qubit(), key) for key in range(3))
        ys = array(Record(qubit(), key) for key in range(3))
        value = Record(qubit(), 1)
        output("equal", xs == ys)
        output("contains", xs.contains(value))
        # Reuse every borrowed linear input, then consume each qubit once.
        output("retained", value.key)
        discard(value.q)
        for record in xs:
            discard(record.q)
        for record in ys:
            discard(record.q)

    result = main.emulator(7).coinflip_sim().run()[0]
    assert result.entries == [
        ("compare", 0),
        ("compare", 1),
        ("compare", 2),
        ("equal", True),
        ("compare", 0),
        ("compare", 1),
        ("contains", True),
        ("retained", 1),
    ]


@pytest.mark.parametrize("operation", ["get_static", "first", "last"])
@no_type_check
def test_static_access_rejects_empty(operation: str) -> None:
    access = getattr(array, operation)
    if operation == "get_static":

        @guppy
        def main(xs: array[int, 0]) -> int:
            return access(xs, 0)
    else:

        @guppy
        def main(xs: array[int, 0]) -> int:
            return access(xs)

    # Empty last() computes -1, which cannot be passed as a nat index.
    diagnostic = (
        "Expected expression of type `nat`" if operation == "last" else "out of bounds"
    )
    with pytest.raises(GuppyError, match=diagnostic):
        main.compile_function()


@no_type_check
def test_static_access_rejects_past_end() -> None:
    @guppy
    def main(xs: array[int, 2]) -> int:
        return xs.get_static(2)

    with pytest.raises(GuppyError, match="out of bounds"):
        main.compile_function()
