import pytest

import guppylang.std.qsystem.helios as helios_mod
import guppylang.std.qsystem.helios.functional as helios_fn_mod
import guppylang.std.qsystem.sol as sol_mod
import guppylang.std.qsystem.sol.functional as sol_fn_mod
from guppylang.decorator import guppy
from guppylang.std.angles import angle
from guppylang.std.builtins import array, owned
from guppylang.std.lang import comptime
from guppylang.std.qsystem.random import RNG, make_discrete_distribution
from guppylang.std.qsystem.utils import get_current_shot
from guppylang.std.quantum import Measurement, measure_array, qubit, x


@pytest.fixture(
    params=[
        pytest.param(helios_mod, id="helios"),
        pytest.param(sol_mod, id="sol"),
    ]
)
def qsys_mod(request):  # type: ignore[no-untyped-def]
    """Fixture providing either the helios or sol qsystem module."""
    return request.param


@pytest.fixture(
    params=[
        pytest.param((helios_mod, helios_fn_mod), id="helios"),
        pytest.param((sol_mod, sol_fn_mod), id="sol"),
    ]
)
def qsys_mod_fn(request):  # type: ignore[no-untyped-def]
    """Fixture providing (inout_module, functional_module) for helios or sol."""
    return request.param


def test_qsystem_helios(validate):  # type: ignore[no-untyped-def]
    """Compile various operations from the qsystem.helios extension."""
    from guppylang.std.qsystem.helios.functional import (
        measure,
        measure_and_reset,
        phased_x,
        qfree,
        reset,
        rz,
        zz_max,
        zz_phase,
    )

    @guppy
    def test(q1: qubit @ owned, q2: qubit @ owned, a1: angle) -> Measurement:
        shot = get_current_shot()
        q1 = phased_x(q1, a1, a1)
        q1, q2 = zz_phase(q1, q2, a1)
        q1 = rz(q1, a1)
        q1, q2 = zz_max(q1, q2)
        q1, msmt1 = measure_and_reset(q1)
        msmt1.read()
        q1 = reset(q1)
        msmt2 = measure(q1)
        qfree(q2)
        return msmt2

    validate(test.compile_function())


def test_qsystem_random(validate):  # type: ignore[no-untyped-def]
    """Compile various operations from the qsystem random extension."""
    from guppylang.std.qsystem.helios import collect_measurements

    @guppy
    def test() -> tuple[int, float, int, int, angle, angle]:
        rng = RNG(42)
        rint = rng.random_int()
        rfloat = rng.random_float()
        rint_bnd = rng.random_int_bounded(100)
        ar = array(qubit() for _ in range(5))
        rng.shuffle(ar)
        _ = collect_measurements(measure_array(ar))
        dist = make_discrete_distribution(array(0.0, 1.0, 2.0, 3.0))
        rint_discrete = dist.sample(rng)
        rangle = rng.random_angle()
        rcangle = rng.random_clifford_angle()
        rng.discard()

        return rint, rfloat, rint_bnd, rint_discrete, rangle, rcangle

    validate(test.compile_function())


def test_random_advance(validate, run_int_fn):  # type: ignore[no-untyped-def]
    """Validate behavior of random_advance from qsystem random extension."""

    @guppy
    def test() -> int:
        rng = RNG(42)
        rint_bnd1 = rng.random_int_bounded(100)
        rng.random_advance(-1)
        rint_bnd2 = rng.random_int_bounded(100)
        same = rint_bnd1 == rint_bnd2
        rng.discard()

        return int(same)

    validate(test.compile_function())
    run_int_fn(test, 1)


# TODO: run emulation when sol platform targeting is available, see
# https://github.com/Quantinuum/guppylang/issues/1797
def test_qsystem_sol(validate):  # type: ignore[no-untyped-def]
    """Compile shared + Sol-specific operations from the qsystem.sol extension."""
    NUM_QUBITS = 3
    from guppylang.std.qsystem.sol import (
        collect_measurements,
        lazy_measure_and_reset,
        lazy_measure_and_reset_array,
        measure,
        measure_and_reset,
        measure_and_reset_array,
        measure_array,
        lazy_measure_array,
        phased_x,
        phased_xx,
        phased_xx_max,
        xx_max,
        qfree,
        reset,
        rz,
    )

    @guppy
    def test(q1: qubit @ owned, q2: qubit @ owned, a1: angle) -> Measurement:
        phased_x(q1, a1, a1)
        phased_xx(q1, q2, a1, a1)
        phased_xx_max(q1, q2, a1)
        xx_max(q1, q2)
        rz(q1, a1)
        m1 = lazy_measure_and_reset(q1)
        m1.read()
        reset(q1)
        b = measure_and_reset(q1)
        b.read()
        reset(q1)
        b = measure(q1)
        qfree(q2)
        return b

    @guppy
    def test_arrays(
        qubits: array[qubit, comptime(NUM_QUBITS)] @ owned,
    ) -> array[Measurement, comptime(NUM_QUBITS)]:
        ms = measure_array(qubits)
        qa = array(qubit() for _ in range(comptime(NUM_QUBITS)))
        ms2 = lazy_measure_array(qa)
        collect_measurements(ms2)
        qb = array(qubit() for _ in range(comptime(NUM_QUBITS)))
        ms3 = measure_and_reset_array(qb)
        collect_measurements(ms3)
        ms4 = lazy_measure_and_reset_array(qb)
        collect_measurements(ms4)
        collect_measurements(measure_array(qb))
        return ms

    validate(test.compile_function())
    validate(test_arrays.compile_function())


# TODO: run emulation when sol platform targeting is available, see
# https://github.com/Quantinuum/guppylang/issues/1797
def test_qsystem_sol_functional(validate):  # type: ignore[no-untyped-def]
    """Compile Sol-specific functional operations."""
    NUM_QUBITS = 3
    from guppylang.std.qsystem.sol import collect_measurements
    from guppylang.std.qsystem.sol.functional import (
        lazy_measure_and_reset,
        lazy_measure_and_reset_array,
        measure,
        measure_and_reset,
        measure_and_reset_array,
        measure_array,
        phased_x,
        phased_xx,
        phased_xx_max,
        qfree,
        reset,
        rz,
        xx_max,
    )

    @guppy
    def test(q1: qubit @ owned, q2: qubit @ owned, a1: angle) -> Measurement:
        q1 = phased_x(q1, a1, a1)
        q1, q2 = phased_xx(q1, q2, a1, a1)
        q1, q2 = phased_xx_max(q1, q2, a1)
        q1, q2 = xx_max(q1, q2)
        q1 = rz(q1, a1)
        q1 = reset(q1)
        q1, m1 = measure_and_reset(q1)
        m1.read()
        q1, m2 = lazy_measure_and_reset(q1)
        m2.read()
        q1 = reset(q1)
        qfree(q2)
        return measure(q1)

    @guppy
    def test_arrays(
        qubits: array[qubit, comptime(NUM_QUBITS)] @ owned,
    ) -> array[Measurement, comptime(NUM_QUBITS)]:
        ms = measure_array(qubits)
        qa = array(qubit() for _ in range(comptime(NUM_QUBITS)))
        qb, ms2 = measure_and_reset_array(qa)
        collect_measurements(ms2)
        qc, ms3 = lazy_measure_and_reset_array(qb)
        collect_measurements(ms3)
        collect_measurements(measure_array(qc))
        return ms

    validate(test.compile_function())
    validate(test_arrays.compile_function())


def test_measure_leaked(validate, qsys_mod):  # type: ignore[no-untyped-def]
    """Compile the measure_leaked operation."""
    measure_leaked = qsys_mod.measure_leaked
    MaybeLeaked = qsys_mod.MaybeLeaked

    @guppy
    def test(q: qubit @ owned) -> bool:
        ml: MaybeLeaked = measure_leaked(q)
        if ml.is_leaked():
            ml.discard()
            return False
        b: bool = ml.to_result().unwrap()
        return b

    validate(test.compile_function())


def test_lazy_measure(validate, qsys_mod):  # type: ignore[no-untyped-def]
    lazy_measure = qsys_mod.lazy_measure

    @guppy
    def test(q: qubit @ owned) -> bool:
        f = lazy_measure(q)
        return f.read()

    validate(test.compile_function())


def test_lazy_measure_conditional(validate, run_int_fn, qsys_mod):  # type: ignore[no-untyped-def]
    lazy_measure = qsys_mod.lazy_measure

    @guppy
    def test() -> int:
        q = qubit()
        x(q)
        if lazy_measure(q):
            return 1
        return 0

    validate(test.compile_function())
    run_int_fn(test, 1, num_qubits=1)


def test_lazy_measure_array(validate, run_int_fn, qsys_mod):  # type: ignore[no-untyped-def]
    NUM_QUBITS = 5
    lazy_measure_array = qsys_mod.lazy_measure_array
    collect_measurements = qsys_mod.collect_measurements

    @guppy
    def test() -> int:
        qubits = array(qubit() for _ in range(comptime(NUM_QUBITS)))
        for i in range(len(qubits)):
            x(qubits[i])
        measurements = lazy_measure_array(qubits)
        results = collect_measurements(measurements)
        sum = 0
        for r in results:
            sum += int(r)
        return sum

    validate(test.compile_function())
    run_int_fn(test, NUM_QUBITS, num_qubits=NUM_QUBITS)


def test_lazy_measure_and_reset(validate, run_int_fn, qsys_mod):  # type: ignore[no-untyped-def]
    lazy_measure_and_reset = qsys_mod.lazy_measure_and_reset
    _measure = qsys_mod.measure

    @guppy
    def test() -> int:
        q = qubit()
        x(q)
        first_result = lazy_measure_and_reset(q)
        second_result = _measure(q)
        if first_result and not second_result:  # First expect flip, then expect reset
            return 1
        return 0

    validate(test.compile_function())
    run_int_fn(test, 1, num_qubits=1)


def test_lazy_measure_and_reset_functional(validate, run_int_fn, qsys_mod_fn):  # type: ignore[no-untyped-def]
    _, fn_mod = qsys_mod_fn
    lazy_measure_and_reset_fn = fn_mod.lazy_measure_and_reset
    _measure = fn_mod.measure

    @guppy
    def test() -> int:
        q = qubit()
        x(q)
        q, first_result = lazy_measure_and_reset_fn(q)
        second_result = _measure(q).read()
        if first_result.read() and not second_result:
            return 1
        return 0

    validate(test.compile_function())
    run_int_fn(test, 1, num_qubits=1)


def test_measure_and_reset_array(validate, run_int_fn, qsys_mod):  # type: ignore[no-untyped-def]
    NUM_QUBITS = 5
    measure_and_reset_array = qsys_mod.measure_and_reset_array
    qsystem_measure_array = qsys_mod.measure_array
    collect_measurements = qsys_mod.collect_measurements

    @guppy
    def test() -> int:
        qubits = array(qubit() for _ in range(comptime(NUM_QUBITS)))
        pattern = array(1, 0, 1, 1, 0)
        for i in range(len(qubits)):
            if pattern[i]:
                x(qubits[i])

        first = collect_measurements(measure_and_reset_array(qubits))
        second = collect_measurements(qsystem_measure_array(qubits))

        for i in range(len(first)):
            if int(first[i]) != pattern[i] or second[i]:
                return 0
        return 1

    validate(test.compile_function())
    run_int_fn(test, 1, num_qubits=NUM_QUBITS)


def test_measure_array_functional(validate, run_int_fn, qsys_mod_fn):  # type: ignore[no-untyped-def]
    NUM_QUBITS = 5
    qsys, fn_mod = qsys_mod_fn
    measure_array_fn = fn_mod.measure_array
    collect_measurements = qsys.collect_measurements

    @guppy
    def test() -> int:
        qubits = array(qubit() for _ in range(comptime(NUM_QUBITS)))
        pattern = array(1, 0, 1, 1, 0)
        for i in range(len(qubits)):
            if pattern[i]:
                x(qubits[i])

        bits = collect_measurements(measure_array_fn(qubits))

        for i in range(len(bits)):
            if int(bits[i]) != pattern[i]:
                return 0
        return 1

    validate(test.compile_function())
    run_int_fn(test, 1, num_qubits=NUM_QUBITS)


def test_measure_and_reset_array_functional(validate, run_int_fn, qsys_mod_fn):  # type: ignore[no-untyped-def]
    NUM_QUBITS = 5
    qsys, fn_mod = qsys_mod_fn
    measure_and_reset_array_fn = fn_mod.measure_and_reset_array
    collect_measurements = qsys.collect_measurements

    @guppy
    def test() -> int:
        qubits = array(qubit() for _ in range(comptime(NUM_QUBITS)))
        pattern = array(1, 0, 1, 1, 0)
        for i in range(len(qubits)):
            if pattern[i]:
                x(qubits[i])

        qubits, first_msmts = measure_and_reset_array_fn(qubits)
        first = collect_measurements(first_msmts)
        second = collect_measurements(measure_array(qubits))

        for i in range(len(first)):
            if int(first[i]) != pattern[i] or second[i]:
                return 0
        return 1

    validate(test.compile_function())
    run_int_fn(test, 1, num_qubits=NUM_QUBITS)


def test_lazy_measure_and_reset_array_functional(validate, run_int_fn, qsys_mod_fn):  # type: ignore[no-untyped-def]
    NUM_QUBITS = 5
    qsys, fn_mod = qsys_mod_fn
    lazy_measure_and_reset_array_fn = fn_mod.lazy_measure_and_reset_array
    qsystem_measure_array = qsys.measure_array
    collect_measurements = qsys.collect_measurements

    @guppy
    def test() -> int:
        qubits = array(qubit() for _ in range(comptime(NUM_QUBITS)))
        pattern = array(1, 0, 1, 1, 0)
        for i in range(len(qubits)):
            if pattern[i]:
                x(qubits[i])

        qubits, first_msmts = lazy_measure_and_reset_array_fn(qubits)
        first = collect_measurements(first_msmts)
        second = collect_measurements(qsystem_measure_array(qubits))

        for i in range(len(first)):
            if int(first[i]) != pattern[i] or second[i]:
                return 0
        return 1

    validate(test.compile_function())
    run_int_fn(test, 1, num_qubits=NUM_QUBITS)
