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


BOOLEAN_PAIRS = [
    ("empty", (), ()),
    ("false-false", (False,), (False,)),
    ("false-true", (False,), (True,)),
    ("true-false", (True,), (False,)),
    ("true-true", (True,), (True,)),
    (
        "truth-table",
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
def test_boolean_logic(
    validate: Callable[..., None], target_platform: Platform
) -> None:
    cases = BOOLEAN_PAIRS

    def program(size: int):
        @guppy
        def main(xs: array[bool, size], ys: array[bool, size]) -> None:
            original_xs = xs.copy()
            original_ys = ys.copy()
            if size:
                output("and", xs.bitwise_and(ys))
                output("or", xs.bitwise_or(ys))
                output("xor", xs.bitwise_xor(ys))
                output("not", xs.bitwise_not())
            else:
                # The output backend rejects empty arrays; check their lengths instead.
                output("and", len(xs.bitwise_and(ys)))
                output("or", len(xs.bitwise_or(ys)))
                output("xor", len(xs.bitwise_xor(ys)))
                output("not", len(xs.bitwise_not()))
            output("dot", xs.dot(ys))
            unchanged = True
            for i in range(size):
                unchanged = (
                    unchanged and xs[i] == original_xs[i] and ys[i] == original_ys[i]
                )
            output("unchanged", unchanged)

        return main

    empty, one, many = [program(size) for size in [0, 1, 5]]

    @guppy
    def main(xs: array[bool, 5], ys: array[bool, 5], size: int) -> None:
        if size == 0:
            empty(array(), array())
        elif size == 1:
            one(array(xs[0]), array(ys[0]))
        else:
            many(xs, ys)

    validate(main.compile_function())
    results = (
        main.emulator(0, platform=target_platform)
        .coinflip_sim()
        .run_per_shot(
            [
                {
                    "xs": list(xs) + [False] * (5 - len(xs)),
                    "ys": list(ys) + [False] * (5 - len(ys)),
                    "size": len(xs),
                }
                for _, xs, ys in cases
            ]
        )
    )
    for (name, xs, ys), shot in zip(cases, results, strict=True):
        size = len(xs)
        assert dict(shot.entries) == {
            "and": [x & y for x, y in zip(xs, ys, strict=True)] if size else 0,
            "or": [x | y for x, y in zip(xs, ys, strict=True)] if size else 0,
            "xor": [x ^ y for x, y in zip(xs, ys, strict=True)] if size else 0,
            "not": [not x for x in xs] if size else 0,
            "dot": bool(sum(x & y for x, y in zip(xs, ys, strict=True)) % 2),
            "unchanged": True,
        }, f"Case {name}: {xs!r}, {ys!r}"
