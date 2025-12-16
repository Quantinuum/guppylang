from guppylang.decorator import guppy
from guppylang.defs import GuppyFunctionDefinition
from guppylang.emulator.exceptions import EmulatorBuildError
from guppylang.std.builtins import result, array, comptime, exit, panic
from guppylang.std.debug import state_result
from guppylang.std.quantum import (
    maybe_qubit,
    project_z,
    z,
    s,
    rz,
    cx,
    crz,
    discard,
    qubit,
    measure,
    h,
    x,
    t,
    measure_array,
)
from guppylang.std.angles import angle, pi
from guppylang.std.qsystem import zz_max, zz_phase, phased_x, rz as qsystem_rz
from guppylang.std.qsystem.utils import get_current_shot
from guppylang.emulator import EmulatorResult, EmulatorError
from selene_sim.backends.bundled_runtimes import SoftRZRuntime


from datetime import timedelta
from selene_sim.backends.bundled_simulators import Stim
from selene_sim.backends.bundled_error_models import IdealErrorModel
from selene_sim.event_hooks import NoEventHook
from selene_sim.exceptions import SelenePanicError


import pytest


def test_basic_emulation() -> None:
    @guppy
    def main() -> None:
        result("c", measure(qubit()))

    res = main.emulator(1).run()
    expected = EmulatorResult([[("c", False)]])
    assert res == expected

    @guppy
    def main() -> None:
        q = qubit()
        h(q)
        result("c", measure(q))

    res = main.emulator(1).statevector_sim().with_seed(42).run()
    expected = EmulatorResult([[("c", True)]])
    assert res == expected


def test_all_options() -> None:
    """Test that all configuration options are properly set and accessible."""

    @guppy
    def main() -> None:
        return

    em = main.emulator(1)

    # Test all configuration methods
    configured_em = (
        em.with_shots(100)
        .with_simulator(Stim())
        .with_runtime(SoftRZRuntime())
        .with_error_model(IdealErrorModel())
        .with_event_hook(NoEventHook())
        .with_verbose(True)
        .with_timeout(timedelta(seconds=30))
        .with_seed(12345)
        .with_shot_offset(10)
        .with_shot_increment(2)
        .with_n_processes(4)
    )

    # Verify all properties are set correctly
    assert configured_em.shots == 100
    assert isinstance(configured_em.simulator, Stim)
    assert isinstance(configured_em.runtime, SoftRZRuntime)
    assert isinstance(configured_em.error_model, IdealErrorModel)
    assert configured_em.verbose is True
    assert configured_em.timeout == timedelta(seconds=30)
    assert configured_em.seed == 12345
    assert configured_em.shot_offset == 10
    assert configured_em.shot_increment == 2
    assert configured_em.n_processes == 4

    result = configured_em.run()
    assert isinstance(result, EmulatorResult)


def test_no_given_qubits() -> None:
    @guppy()
    def main() -> None:
        result("c", measure(qubit()))

    with pytest.raises(
        EmulatorBuildError,
        match=(
            r"Number of qubits to be used must be specified, either as an argument to "
            r"`emulator` or hinted on the entrypoint function using "
            r"`@guppy\(max_qubits=...\)`."
        ),
    ):
        main.emulator().coinflip_sim().with_seed(0).with_shots(1).run()


def test_hinted_qubits() -> None:
    @guppy(max_qubits=1)
    def main() -> None:
        result("c", measure(qubit()))

    shots = main.emulator().coinflip_sim().with_seed(0).with_shots(1).run()
    assert shots[0].as_dict()["c"] == 1


def test_hinted_qubits_with_given_qubits() -> None:
    @guppy(max_qubits=1)
    def main() -> None:
        qubits = array(qubit() for _ in range(4))
        result("c", measure_array(qubits))

    shots = main.emulator(n_qubits=4).coinflip_sim().with_seed(0).with_shots(1).run()
    assert shots[0].as_dict()["c"] == [1, 0, 1, 0]


def test_hinted_qubits_with_insufficient_given_qubits() -> None:
    @guppy(max_qubits=3)
    def main() -> None:
        result("c", measure(qubit()))

    with pytest.raises(
        EmulatorBuildError,
        match=(
            r"Number of qubits requested \(1\) is insufficient to cover the maximum "
            r"number of qubits hinted on the entrypoint \(3\)."
        ),
    ):
        main.emulator(n_qubits=1).coinflip_sim().with_seed(0).with_shots(1).run()


def test_statevector() -> None:
    @guppy
    def main() -> None:
        q = qubit()
        x(q)
        state_result("s", q)
        state_result("s", q)
        result("c", measure(q))

    res = main.emulator(1).run()
    (shot_states,) = res.partial_states()
    assert len(shot_states) == 2
    assert all(tag == "s" for tag, _ in shot_states)

    # repeated tag causes overwrite
    assert res.partial_state_dicts() == [{"s": shot_states[1][1]}]


def _build_run(
    program: GuppyFunctionDefinition,
    n_qubits: int = 4,
    n_shots: int = 1,
    seed: int | None = None,
) -> EmulatorResult:
    return program.emulator(n_qubits).with_shots(n_shots).with_seed(seed).run()


def test_zeros():
    N = 2

    @guppy
    def main() -> array[qubit, comptime(N)]:
        q = array(qubit(), qubit())
        for i in range(comptime(N)):
            result("c", project_z(q[i]))
        return q

    res = _build_run(main, n_qubits=N).results[0].entries
    assert res == [("c", 0)] * N


def test_4pi():
    @guppy
    def main() -> None:
        aux, tgt = qubit(), qubit()

        h(aux)
        z(tgt)

        s(aux)
        h(tgt)

        theta = -pi
        crz(aux, tgt, theta)

        # correct implementation:
        # zz_phase(aux, tgt, -theta / 2)
        # rz(tgt, theta / 2)

        h(tgt)
        z(tgt)

        # bell measurement
        cx(aux, tgt)
        h(aux)

        result("aux", measure(aux))
        discard(tgt)

    res = _build_run(main, n_qubits=2, n_shots=1).results[0].entries
    # deterministic - should always be 0
    # with buggy crz implementation which assumes angle is equivalent modulo 2pi,
    # it's always 1
    assert res == [("aux", 0)]


def test_qsystem():
    @guppy
    def main() -> None:
        a, b = qubit(), qubit()
        h(a)
        h(b)

        # Full rotation, just an identity
        zz_max(a, b)
        zz_phase(
            a,
            b,
            angle(1 / 2) * 3,
        )

        # Some here
        # phased_x(2, 1/3) = I
        phased_x(
            a,
            angle(3 / 2) / 3.0 - angle(-3 / 2),
            -angle(1 / 3),
        )
        # Rz(-1/2) Rz(1/2) = I
        rz(a, angle(1 / 2))
        qsystem_rz(a, -angle(1 / 2))

        h(a)
        h(b)
        result("a", measure(a))
        result("b", measure(b))

    # deterministic - should always be 0
    res = _build_run(main, n_qubits=2)
    for r in res.results:
        assert r.entries == [("a", 0), ("b", 0)]


def test_alloc_free():
    from guppylang.std.qsystem import measure, measure_and_reset, qfree, reset

    @guppy
    def main() -> None:
        q0 = maybe_qubit().unwrap()
        x(q0)
        b1 = measure_and_reset(q0)
        q1 = qubit()
        reset(q1)
        qfree(q1)
        b2 = project_z(q0)
        result("c0", b1)
        result("c1", b2)
        result("c2", measure(q0))

    res = _build_run(main, n_qubits=2, n_shots=1, seed=12).results[0].entries
    assert dict(res) == {"c0": 1, "c1": 0, "c2": 0}


def test_multi_alloc_free():
    N = 4

    @guppy
    def main() -> None:
        for _ in range(comptime(N)):
            q = qubit()
            result("c", measure(q))

    res = _build_run(main, n_qubits=2).results[0].entries
    assert res == [("c", 0)] * N


def test_user_panic() -> None:
    """Test a panic as issued explicitly by the user program.

    This should abort the current shot and all subsequent shots, raising
    an EmulatorError to provide access to completed shots, the failing shot,
    and the underlying exception raised by Selene.
    """

    @guppy
    def main() -> None:
        current_shot = get_current_shot()
        result("before", current_shot)
        if current_shot == 9:
            panic("Panic at shot 9!")
        result("after", current_shot)

    with pytest.raises(EmulatorError, match="Panic at shot 9!") as exc_info:
        main.emulator(1).with_shots(20).run()

    exception: EmulatorError = exc_info.value
    assert isinstance(exception.underlying_exception, SelenePanicError)
    assert exception.failed_shot_index == 9
    assert exception.completed_shots == EmulatorResult(
        [[("before", i), ("after", i)] for i in range(9)]
    )
    assert exception.failing_shot.entries == [("before", 9)]


def test_friendly_emulator_panic() -> None:
    """Test a panic as issued by the emulator due to a configuration
    issue.

    As with the user panic, this should abort the current shot and all
    subsequent shots, raising an EmulatorError to provide access to completed
    shots, the failing shot, and the underlying exception raised by Selene.

    But this time, the error isn't immediately apparent from the guppy
    program itself. It is instead caused by the wrong choice of simulator
    (a stabilizer simulator being used for a non-clifford circuit).

    As the error is triggered within the emulator, we should see the error
    details within the internal error provided by stdout and/or stderr.
    """

    @guppy
    def main() -> None:
        q = qubit()
        current_shot = get_current_shot()
        result("shot", current_shot)
        if current_shot == 5:
            t(q)
        result("measurement", measure(q))

    with pytest.raises(
        EmulatorError, match="not representable in stabiliser form"
    ) as exc_info:
        main.emulator(1).stabilizer_sim().with_shots(10).run()

    exception: EmulatorError = exc_info.value
    assert isinstance(exception.underlying_exception, SelenePanicError)
    assert exception.failed_shot_index == 5
    assert exception.completed_shots == EmulatorResult(
        [[("shot", i), ("measurement", False)] for i in range(5)]
    )
    assert exception.failing_shot.entries == [("shot", 5)]


def test_exit():
    """Test an exit ends a shot early but continues subsequent shots."""
    N = 10

    @guppy
    def main() -> None:
        i = get_current_shot()
        if i % 2 == 0:
            exit("even!", 0)
        result("c", i)

    res = _build_run(main, n_qubits=2, n_shots=N)
    assert res == EmulatorResult(
        [[("c", i)] if i % 2 != 0 else [("exit: even!", 0)] for i in range(N)]
    )


def test_static_array_bool():
    @guppy
    def main() -> None:
        q = comptime([[x % 2 == 0 for x in range(100)] for _ in range(100)])
        result("a", q[50][50])
        result("b", q[51][51])

    res = _build_run(main, n_qubits=1).results[0].entries
    assert res == [("a", True), ("b", False)]
