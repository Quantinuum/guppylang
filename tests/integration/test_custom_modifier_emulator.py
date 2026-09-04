"""Runtime tests for custom unitary modifier definitions."""

from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.builtins import control, dagger
from guppylang.std.quantum import discard, discard_array, measure, qubit, x


def test_controlled_impl_is_executed(use_experimental_features, run_int_fn):
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
    def main() -> int:
        target = qubit()
        control_qubit = qubit()
        x(control_qubit)
        with control(control_qubit):
            custom_gate(target)
        result = measure(target).read()
        discard(control_qubit)
        return 1 if result else 0

    run_int_fn(main, expected=1, num_qubits=2)


def test_daggered_impl_is_executed(use_experimental_features, run_int_fn):
    @guppy.unitary
    class custom_gate:
        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def daggered(q: qubit) -> None:
            x(q)

    @guppy
    def main() -> int:
        target = qubit()
        with dagger:
            custom_gate(target)
        return 1 if measure(target).read() else 0

    run_int_fn(main, expected=1, num_qubits=1)


def test_ctrl_daggered_impl_is_executed(use_experimental_features, run_int_fn):
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
    def main() -> int:
        target = qubit()
        control_qubit = qubit()
        x(control_qubit)
        with control(control_qubit), dagger:
            custom_gate(target)
        result = measure(target).read()
        discard(control_qubit)
        return 1 if result else 0

    run_int_fn(main, expected=1, num_qubits=2)


def test_two_control_counts_distinct_runtime(use_experimental_features, run_int_fn):
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
    def main() -> int:
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

        result_one = measure(target_one).read()
        result_two = measure(target_two).read()
        discard(control_one)
        discard_array(controls_two)
        return (1 if result_one else 0) + (2 if result_two else 0)

    run_int_fn(main, expected=3, num_qubits=5)
