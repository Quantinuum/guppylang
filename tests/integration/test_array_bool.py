"""Focused execution tests for boolean array utilities."""

from itertools import batched
from typing import no_type_check

from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.num import nat
from guppylang.std.platform import output


REDUCTION_CASES = [
    ("empty", ()),
    ("singleton_false", (False,)),
    ("singleton_true", (True,)),
    ("all_false", (False, False, False)),
    ("all_true_odd", (True, True, True)),
    ("first_true", (True, False, False)),
    ("middle_true", (False, True, False)),
    ("last_true", (False, False, True)),
    ("mixed_even", (True, False, True)),
]


# Compile-time harnesses call generic Guppy helpers for all cases in one shot.
@no_type_check
def test_boolean_reductions() -> None:
    cases = REDUCTION_CASES

    @guppy
    def check[size: nat](xs: array[bool, size]) -> None:
        original = xs.copy()
        output("any", xs.any())
        output("all", xs.all())
        output("count_true", xs.count_true())
        output("parity", xs.parity())
        unchanged = True
        for i in range(size):
            unchanged = unchanged and xs[i] == original[i]
        output("unchanged", unchanged)

    @guppy
    def empty() -> None:
        check(array())

    @guppy.comptime
    def main() -> None:
        empty()
        for _, values in cases:
            if values:
                check(list(values))

    shot = main.emulator(0).coinflip_sim().run()[0]
    for (name, values), entries in zip(cases, batched(shot.entries, 5), strict=True):
        assert dict(entries) == {
            "any": any(values),
            "all": all(values),
            "count_true": sum(values),
            "parity": bool(sum(values) % 2),
            "unchanged": True,
        }, f"Case {name}: {values!r}"


BOOLEAN_PAIRS = [
    ("empty", (), ()),
    ("false_false", (False,), (False,)),
    ("false_true", (False,), (True,)),
    ("true_false", (True,), (False,)),
    ("true_true", (True,), (True,)),
    (
        "truth_table",
        (False, False, True, True, False),
        (False, True, False, True, True),
    ),
    (
        "asymmetric",
        (True, False, True, False, True),
        (False, False, True, True, True),
    ),
]


@no_type_check
def test_boolean_logic() -> None:
    cases = BOOLEAN_PAIRS

    @guppy
    def check[size: nat](xs: array[bool, size], ys: array[bool, size]) -> None:
        original_xs = xs.copy()
        original_ys = ys.copy()
        if size:
            output("and", xs.bitwise_and(ys))
            output("or", xs.bitwise_or(ys))
            output("xor", xs.bitwise_xor(ys))
            output("not", xs.bitwise_not())
        else:
            xs.bitwise_and(ys)
            xs.bitwise_or(ys)
            xs.bitwise_xor(ys)
            xs.bitwise_not()
            xs.dot(ys)
            return
        output("dot", xs.dot(ys))
        unchanged = True
        for i in range(size):
            unchanged = (
                unchanged and xs[i] == original_xs[i] and ys[i] == original_ys[i]
            )
        output("unchanged", unchanged)

    @guppy
    def empty() -> None:
        check(array(), array())

    @guppy.comptime
    def main() -> None:
        empty()
        for _, xs, ys in cases:
            if xs:
                check(list(xs), list(ys))

    shot = main.emulator(0).coinflip_sim().run()[0]
    entries = iter(shot.entries)
    for name, xs, ys in cases:
        # Empty operations are smoke-checked without output.
        if not xs:
            continue
        expected = {
            "and": [x & y for x, y in zip(xs, ys, strict=True)],
            "or": [x | y for x, y in zip(xs, ys, strict=True)],
            "xor": [x ^ y for x, y in zip(xs, ys, strict=True)],
            "not": [not x for x in xs],
            "dot": bool(sum(x & y for x, y in zip(xs, ys, strict=True)) % 2),
            "unchanged": True,
        }
        assert dict(next(entries) for _ in expected) == expected, name
    assert next(entries, None) is None
