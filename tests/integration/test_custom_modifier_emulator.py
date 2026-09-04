"""Runtime tests for custom unitary modifier definitions."""

from guppylang import guppy
from guppylang.emulator import EmulatorResult
from guppylang.std.array import array
from guppylang.std.builtins import control, dagger, output
from guppylang.std.quantum import discard, discard_array, measure, qubit, x


def test_controlled_impl_is_executed(use_experimental_features):
    @guppy.unitary
    class custom_gate:
        n = guppy.nat_var("n")

        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled(q: qubit, _controls: array[qubit, n]) -> None:
            x(q)

    @guppy
    def main() -> None:
        target = qubit()
        control_qubit = qubit()
        x(control_qubit)
        with control(control_qubit):
            custom_gate(target)
        output("target", measure(target).read())
        discard(control_qubit)

    result = main.emulator(2).statevector_sim().run()
    assert result == EmulatorResult([[("target", True)]])


def test_daggered_impl_is_executed(use_experimental_features):
    @guppy.unitary
    class custom_gate:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def daggered(q: qubit) -> None:
            x(q)

    @guppy
    def main() -> None:
        target = qubit()
        with dagger:
            custom_gate(target)
        output("target", measure(target).read())

    result = main.emulator(1).statevector_sim().run()
    assert result == EmulatorResult([[("target", True)]])


def test_ctrl_daggered_impl_is_executed(use_experimental_features):
    @guppy.unitary
    class custom_gate:
        n = guppy.nat_var("n")

        @guppy(controllable=True)
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def ctrl_daggered(q: qubit, _controls: array[qubit, n]) -> None:
            x(q)

    @guppy
    def main() -> None:
        target = qubit()
        control_qubit = qubit()
        x(control_qubit)
        with control(control_qubit), dagger:
            custom_gate(target)
        output("target", measure(target).read())
        discard(control_qubit)

    result = main.emulator(2).statevector_sim().run()
    assert result == EmulatorResult([[("target", True)]])


def test_two_control_counts_distinct_runtime(use_experimental_features):
    @guppy.unitary
    class custom_gate:
        n = guppy.nat_var("n")

        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled(q: qubit, _controls: array[qubit, n]) -> None:
            x(q)

    @guppy
    def main() -> None:
        target_one = qubit()
        control_one = qubit()
        x(control_one)
        with control(control_one):
            custom_gate(target_one)

        target_two = qubit()
        control_two_a = qubit()
        control_two_b = qubit()
        x(control_two_a)
        x(control_two_b)
        controls_two = array(control_two_a, control_two_b)
        with control(controls_two):
            custom_gate(target_two)

        output("target_one", measure(target_one).read())
        output("target_two", measure(target_two).read())
        discard(control_one)
        discard_array(controls_two)

    result = main.emulator(5).statevector_sim().run()
    assert result == EmulatorResult([[("target_one", True), ("target_two", True)]])
