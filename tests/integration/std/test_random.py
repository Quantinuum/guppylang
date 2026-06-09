from guppylang import guppy
from guppylang.std.builtins import owned, result
from guppylang.std.quantum import h, measure, qubit, x
from guppylang.std.random import seeded_pcg32


def test_pcg32_compile(validate) -> None:
    @guppy
    def main() -> tuple[int, int]:
        rng = seeded_pcg32(1)
        rng, first = rng.next_int()
        rng, second = rng.next_int()
        return first, second

    validate(main.compile_function())


def test_pcg32_sequence_seed_1(run_int_fn) -> None:
    @guppy
    def main() -> int:
        rng = seeded_pcg32(1)
        rng, first = rng.next_int()
        rng, second = rng.next_int()
        return first + second

    run_int_fn(main, 1307692281 + -444364974)


def test_pcg32_sequence_seed_2(run_int_fn) -> None:
    @guppy
    def main() -> int:
        rng = seeded_pcg32(2)
        _, first = rng.next_int()
        return first

    run_int_fn(main, -8000311)


def test_pcg32_deterministic_sequence(run_int_fn) -> None:
    """First five outputs for initstate=42, initseq=54 match PCG32 reference."""

    @guppy
    def main() -> int:
        rng = seeded_pcg32(54)
        total = 0
        for _ in range(5):
            rng, value = rng.next_int()
            total += value
        return total

    # Reference values from https://rosettacode.org/wiki/Pseudo-random_numbers/PCG32
    expected = sum(
        [
            -1587805513,
            2068313097,
            -1172491472,
            -2083327341,
            -1079740341,
        ]
    )
    run_int_fn(main, expected)


def test_pcg32_motivating_example() -> None:
    """Exact scenario from https://github.com/Quantinuum/guppylang/issues/1578.

    Inner RNG must not affect the outer stream.
    """

    @guppy
    def uses_inner_rng() -> int:
        inner = seeded_pcg32(2)
        _, value = inner.next_int()
        return value

    @guppy
    def main() -> None:
        outer = seeded_pcg32(1)
        outer, first = outer.next_int()

        _ = uses_inner_rng()

        outer, second = outer.next_int()
        result("first", first)
        result("second", second)

    results = dict(
        main.emulator(0).coinflip_sim().with_seed(42).run().results[0].entries
    )
    assert results == {"first": 1307692281, "second": -444364974}


def test_pcg32_independent_streams(validate, run_int_fn) -> None:
    """Inner and outer RNG streams do not interfere with each other."""

    @guppy
    def uses_inner_rng() -> int:
        inner = seeded_pcg32(2)
        _, value = inner.next_int()
        return value

    @guppy
    def main() -> int:
        outer = seeded_pcg32(1)
        outer, first = outer.next_int()
        _ = uses_inner_rng()
        outer, second = outer.next_int()
        return first + second

    validate(main.compile_function())
    run_int_fn(main, 1307692281 + -444364974)


def test_pcg32_no_interference_with_quantum() -> None:
    """Outer RNG is stable across branches; see https://github.com/Quantinuum/guppylang/issues/1578."""

    @guppy
    def some_outside_function(q: qubit @ owned) -> qubit:
        p = qubit()
        if measure(q):
            rng_inner = seeded_pcg32(2)
            _, value = rng_inner.next_int()
            result("rng1_0", value)
            x(p)
        return p

    @guppy
    def main() -> None:
        rng_outer = seeded_pcg32(1)
        rng_outer, value = rng_outer.next_int()
        result("rng0_0", value)

        q = qubit()
        h(q)
        p = some_outside_function(q)
        if measure(p):
            _, value = rng_outer.next_int()
            result("rng0_1", value)
        else:
            _, value = rng_outer.next_int()
            result("rng0_1", value)

    results = main.emulator(2).coinflip_sim().with_seed(42).run().results[0].entries
    entries = dict(results)
    assert entries["rng0_0"] == 1307692281
    assert entries["rng0_1"] == -444364974
    if "rng1_0" in entries:
        assert entries["rng1_0"] == -8000311
