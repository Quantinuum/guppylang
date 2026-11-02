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
