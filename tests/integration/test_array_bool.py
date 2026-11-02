"""Focused execution tests for boolean array utilities."""

from collections.abc import Callable
from typing import no_type_check

from guppylang import guppy
from guppylang.emulator import Platform
from guppylang.std.array import array
from guppylang.std.platform import output


REDUCTION_CASES = [
    ("empty", ()),
    ("singleton-false", (False,)),
    ("singleton-true", (True,)),
    ("all-false", (False, False, False)),
    ("all-true-odd", (True, True, True)),
    ("first-true", (True, False, False)),
    ("middle-true", (False, True, False)),
    ("last-true", (False, False, True)),
    ("mixed-even", (True, False, True)),
]


# Each executable includes all required static sizes; runtime cases use padded
# arguments and select the matching specialization, including internal empty arrays.
@no_type_check
def test_boolean_reductions(
    validate: Callable[..., None], target_platform: Platform
) -> None:
    cases = REDUCTION_CASES

    def program(size: int):
        @guppy
        def main(xs: array[bool, size]) -> None:
            original = xs.copy()
            output("any", xs.any())
            output("all", xs.all())
            output("count_true", xs.count_true())
            output("parity", xs.parity())
            unchanged = True
            for i in range(size):
                unchanged = unchanged and xs[i] == original[i]
            output("unchanged", unchanged)

        return main

    empty, one, many = [program(size) for size in [0, 1, 3]]

    @guppy
    def main(xs: array[bool, 3], size: int) -> None:
        if size == 0:
            empty(array())
        elif size == 1:
            one(array(xs[0]))
        else:
            many(xs)

    validate(main.compile_function())
    results = (
        main.emulator(0, platform=target_platform)
        .coinflip_sim()
        .run_per_shot(
            [
                {"xs": list(values) + [False] * (3 - len(values)), "size": len(values)}
                for _, values in cases
            ]
        )
    )
    for (name, values), shot in zip(cases, results, strict=True):
        size = len(values)
        assert dict(shot.entries) == {
            "any": any(values),
            "all": all(values),
            "count_true": sum(values),
            "parity": bool(sum(values) % 2),
            "unchanged": True,
        }, f"Case {name}: {values!r}"

