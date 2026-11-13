"""Safe access and structurally constrained value comparisons."""

from typing import Self, no_type_check

import pytest

from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.lang import comptime
from guppylang.std.num import nat
from guppylang.std.platform import output
from guppylang.std.quantum import discard, qubit
from guppylang_internals.error import GuppyError


@no_type_check
def test_array_access() -> None:
    # Exercise each runtime boundary independently; endpoint methods are only
    # called on nonempty arrays because they reject empty arrays at compile time.
    cases = [
        ("empty", (), -1),
        ("singleton", (2,), 0),
        ("singleton_past_end", (2,), 1),
        ("negative", (0, 1, 2), -1),
        ("first", (0, 1, 2), 0),
        ("last", (0, 1, 2), 2),
        ("past_end", (0, 1, 2), 3),
    ]

    @guppy
    def check[size: nat](xs: array[int, size], index: int) -> None:
        selected = xs.get(index)
        output("some", selected.is_some())
        if selected.is_some():
            output("value", selected.unwrap())
        output("empty", xs.is_empty())
        if size:
            output("retained", xs)

    @guppy
    def endpoints[size: nat](xs: array[int, size]) -> None:
        output("first", xs.first())
        output("last", xs.last())
        output("static", xs.get_static(0))

    @guppy
    def empty(index: int) -> None:
        # The argument provider cannot infer an empty Python list's element type.
        check(array(), index)

    @guppy.comptime
    def main() -> None:
        # Share compilation across cases and static sizes without runtime dispatch.
        for _, xs, index in cases:
            if xs:
                check(list(xs), index)
                endpoints(list(xs))
            else:
                empty(index)

    entries = iter(main.emulator(0).coinflip_sim().run()[0].entries)
    for name, xs, index in cases:
        present = 0 <= index < len(xs)
        expected = [("some", present)]
        if present:
            expected.append(("value", xs[index]))
        expected.append(("empty", not xs))
        if xs:
            expected.extend(
                [
                    ("retained", list(xs)),
                    ("first", xs[0]),
                    ("last", xs[-1]),
                    ("static", xs[0]),
                ]
            )
        # Each case emits a contiguous group; matching tags also checks its shape.
        assert [next(entries) for _ in expected] == expected, name
    assert next(entries, None) is None


@no_type_check
def test_array_comparisons_and_search() -> None:
    # Equal, early/late mismatch, repeated, and absent values are separate named
    # cases rather than a Cartesian product of unrelated access/search parameters.
    cases = [
        ("empty", (), (), 2),
        ("singleton_match", (2,), (2,), 2),
        ("singleton_miss", (2,), (3,), 9),
        ("first_mismatch", (0, 1, 2), (9, 1, 2), 0),
        ("last_mismatch", (0, 1, 2), (0, 1, 9), 2),
        ("absent", (0, 1, 2), (0, 1, 2), 9),
        ("repeated", (2, 2, 2), (2, 2, 2), 2),
    ]

    @guppy
    def check[size: nat](
        xs: array[int, size], ys: array[int, size], value: int
    ) -> None:
        output("equal", xs == ys)
        output("unequal", xs != ys)
        output("contains", xs.contains(value))
        output("count", xs.count(value))
        # Differing static lengths must compare unequal without element access.
        other = array(0 for _ in range(comptime(size + 1)))
        output("different_length_equal", xs == other)
        output("different_length_unequal", xs != other)
        if size:
            output("retained", xs)
            output("other_retained", ys)

    @guppy
    def empty(value: int) -> None:
        check(array(), array(), value)

    @guppy.comptime
    def main() -> None:
        for _, xs, ys, value in cases:
            if xs:
                check(list(xs), list(ys), value)
            else:
                empty(value)

    entries = iter(main.emulator(0).coinflip_sim().run()[0].entries)
    for name, xs, ys, value in cases:
        expected = {
            "equal": xs == ys,
            "unequal": xs != ys,
            "contains": value in xs,
            "count": xs.count(value),
            "different_length_equal": False,
            "different_length_unequal": True,
        }
        if xs:
            expected.update(retained=list(xs), other_retained=list(ys))
        # The scalar and whole-array tags make each API's result independent.
        assert dict(next(entries) for _ in expected) == expected, name
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


@pytest.mark.parametrize(
    ("operation", "diagnostic"),
    [
        ("get_static", "out of bounds"),
        ("first", "out of bounds"),
        ("last", r"array\.last\(\) requires a non-empty array"),
    ],
)
@no_type_check
def test_static_access_rejects_empty(operation: str, diagnostic: str) -> None:
    access = getattr(array, operation)
    if operation == "get_static":

        @guppy
        def main(xs: array[int, 0]) -> int:
            return access(xs, 0)
    else:

        @guppy
        def main(xs: array[int, 0]) -> int:
            return access(xs)

    with pytest.raises(GuppyError, match=diagnostic):
        main.compile_function()


@no_type_check
def test_static_access_rejects_past_end() -> None:
    @guppy
    def main(xs: array[int, 2]) -> int:
        return xs.get_static(2)

    with pytest.raises(GuppyError, match="out of bounds"):
        main.compile_function()
