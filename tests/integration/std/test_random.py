from guppylang import guppy
from guppylang.std.builtins import owned, output
from guppylang.std.quantum import h, measure, qubit, x
from guppylang.std.qsystem.utils import get_current_shot
from guppylang.std.random import seeded_pcg32

from selene_sim.backends.bundled_simulators import ClassicalReplay


def test_pcg32_compile(validate) -> None:
    @guppy
    def main() -> tuple[int, int]:
        rng = seeded_pcg32(1)
        first = rng.next_int()
        second = rng.next_int()
        return first, second

    # Current tket NormalizeGuppy function inlining over-expands this HUGR and
    # panics in portgraph; keep validating the HUGR locally, but do not export it
    # for tket normalization in CI.
    validate(main.compile_function(), export=False)


def test_pcg32_sequence_seed_1(run_int_fn) -> None:
    @guppy
    def main() -> int:
        rng = seeded_pcg32(1)
        first = rng.next_int()
        second = rng.next_int()
        return first + second

    run_int_fn(main, 1307692281 + -444364974)


def test_pcg32_sequence_seed_2(run_int_fn) -> None:
    @guppy
    def main() -> int:
        rng = seeded_pcg32(2)
        first = rng.next_int()
        return first

    run_int_fn(main, -8000311)


def test_pcg32_deterministic_sequence(run_int_fn) -> None:
    """First five outputs for initstate=42, initseq=54 match PCG32 reference."""

    @guppy
    def main() -> int:
        rng = seeded_pcg32(54)
        total = 0
        for _ in range(5):
            value = rng.next_int()
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
        value = inner.next_int()
        return value

    @guppy
    def main() -> None:
        outer = seeded_pcg32(1)
        first = outer.next_int()

        _ = uses_inner_rng()

        second = outer.next_int()
        output("first", first)
        output("second", second)

        # Repeat with no inner RNG: outer stream must match exactly.
        outer = seeded_pcg32(1)
        other_first = outer.next_int()
        other_second = outer.next_int()
        output("other_first", other_first)
        output("other_second", other_second)

    results = main.emulator(0).coinflip_sim().with_seed(42).run().collated_shots()[0]
    assert results["first"] == results["other_first"] == [1307692281]
    assert results["second"] == results["other_second"] == [-444364974]


def test_pcg32_matches_qsystem_random() -> None:
    """PCG32 and qsystem RNG produce the same values for the same seed."""

    from guppylang.std.qsystem.random import RNG

    @guppy
    def main() -> None:
        pcg = seeded_pcg32(55555)
        output("pcg_int", pcg.next_int())
        output("pcg_bnd2", pcg.next_int_bounded(2))
        output("pcg_bnd6", pcg.next_int_bounded(6))
        output("pcg_bnd100", pcg.next_int_bounded(100))

        qsys = RNG(55555)
        output("qsys_int", qsys.random_int())
        output("qsys_bnd2", qsys.random_int_bounded(2))
        output("qsys_bnd6", qsys.random_int_bounded(6))
        output("qsys_bnd100", qsys.random_int_bounded(100))
        qsys.discard()

    results = main.emulator(0).coinflip_sim().with_seed(42).run().collated_shots()[0]
    assert results["pcg_int"] == results["qsys_int"] == [636174845]
    assert results["pcg_bnd2"] == results["qsys_bnd2"] == [1]
    assert results["pcg_bnd6"] == results["qsys_bnd6"] == [0]
    assert results["pcg_bnd100"] == results["qsys_bnd100"] == [27]


def test_pcg32_no_interference_with_quantum() -> None:
    """Outer RNG is stable across branches; see https://github.com/Quantinuum/guppylang/issues/1578."""

    @guppy
    def some_outside_function(q: qubit @ owned) -> qubit:
        p = qubit()
        if measure(q):
            rng_inner = seeded_pcg32(2)
            value = rng_inner.next_int()
            output("rng1_0", value)
            x(p)
        return p

    @guppy
    def main() -> None:
        rng_outer = seeded_pcg32(1)
        value = rng_outer.next_int()
        output("rng0_0", value)

        q = qubit()
        h(q)
        p = some_outside_function(q)
        if measure(p):
            value = rng_outer.next_int()
            output("rng0_1", value)
        else:
            value = rng_outer.next_int()
            output("rng0_1", value)

    measurements = [
        [False, False],
        [True, True],
        [True, False],
        [False, True],
    ]
    shots = (
        main.emulator(2)
        .with_simulator(ClassicalReplay(measurements=measurements))
        .with_shots(len(measurements))
        .run()
        .collated_shots()
    )
    for shot in shots:
        assert shot["rng0_0"] == [1307692281]
        assert shot["rng0_1"] == [-444364974]
    assert "rng1_0" not in shots[0]
    assert shots[1]["rng1_0"] == [-8000311]
    assert shots[2]["rng1_0"] == [-8000311]
    assert "rng1_0" not in shots[3]


def test_pcg32_bounded_compile(validate) -> None:
    @guppy
    def main() -> int:
        rng = seeded_pcg32(1)
        return rng.next_int_bounded(6)

    validate(main.compile_function())


def test_pcg32_bounded_sequence_seed_1(run_int_fn) -> None:
    @guppy
    def main() -> int:
        rng = seeded_pcg32(1)
        coin = rng.next_int_bounded(2)
        die = rng.next_int_bounded(6)
        hundred = rng.next_int_bounded(100)
        return coin + die + hundred

    run_int_fn(main, 1 + 4 + 4)


def test_pcg32_bounded_sequence_seed_2(run_int_fn) -> None:
    @guppy
    def main() -> int:
        rng = seeded_pcg32(2)
        return rng.next_int_bounded(100)

    run_int_fn(main, 85)


def test_pcg32_bounded_deterministic_sequence(run_int_fn) -> None:
    """Bounded draws for initseq=54 match pcg32_boundedrand_r reference."""

    @guppy
    def main() -> int:
        rng = seeded_pcg32(54)
        total = rng.next_int_bounded(2)
        total += rng.next_int_bounded(6)
        total += rng.next_int_bounded(100)
        return total

    run_int_fn(main, 1 + 3 + 24)


def test_pcg32_bounded_bound_zero_exits() -> None:
    """Invalid bound exits the current shot; subsequent shots still run."""

    @guppy
    def main() -> None:
        if get_current_shot() == 0:
            rng = seeded_pcg32(1)
            _ = rng.next_int_bounded(0)
        else:
            rng = seeded_pcg32(1)
            output("ok", rng.next_int_bounded(6))

    res = main.emulator(0).coinflip_sim().with_shots(2).run()
    assert res.results[0].entries == [
        ("exit: PCG32.next_int_bounded: bound must be positive", 1)
    ]
    assert res.results[1].entries == [("ok", 3)]
