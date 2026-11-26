from guppylang.decorator import guppy

from guppylang.std.array import array
from guppylang.std.builtins import (
    Controllable,
    Daggerable,
    Unitary,
    control,
    dagger,
    nat,
)
from guppylang.std.quantum import discard, h, measure, qubit, x


def test_generic_nat_in_dagger(validate):
    @guppy
    def apply_dagger[n: nat](qs: array[qubit, n]) -> None:
        with dagger:
            h(qs[n - 1])

    @guppy
    def main(qs: array[qubit, 2]) -> None:
        apply_dagger(qs)

    validate(main.compile_function())


def test_higher_order_daggerable_callable(validate):
    """Higher-order arguments can require dagger support."""

    @guppy(daggerable=True)
    def apply_dagger[F: Daggerable[[qubit], None]](f: F, q: qubit) -> None:
        f(q)

    @guppy
    def main(q: qubit) -> None:
        with dagger:
            apply_dagger(h, q)

    validate(main.compile_function())


def test_higher_order_control_controllable_callable(validate):
    """Higher-order arguments can require control support."""

    @guppy(controllable=True)
    def apply_control[F: Controllable[[qubit], None]](
        f: F, ctrl: qubit, q: qubit
    ) -> None:
        with control(ctrl):
            f(q)

    @guppy
    def main(ctrl: qubit, q: qubit) -> None:
        apply_control(h, ctrl, q)

    validate(main.compile_function())


def test_higher_order_unitary_callable(validate):
    """A unitary higher-order argument can be used in a combined modifier context."""

    @guppy(unitary=True)
    def apply_unitary[F: Unitary[[qubit], None]](f: F, ctrl: qubit, q: qubit) -> None:
        with dagger:
            with control(ctrl):
                f(q)

    apply_unitary.check()

    @guppy(unitary=True)
    def foo(q: qubit) -> None:
        pass

    @guppy
    def main(q1: qubit, q2: qubit) -> None:
        apply_unitary(h, q1, q2)
        apply_unitary(foo, q1, q2)

    validate(main.compile_function())


def test_custom_control_with_same_named_callbacks(run_int_fn):
    """Checking modifier behavior with gate factory see: https://github.com/Quantinuum/guppylang/issues/2563"""

    def make_gate(flip: bool):
        @guppy.comptime(unitary=True)
        def gate(q: qubit) -> None:
            if flip:
                x(q)

        return gate

    identity = make_gate(False)
    flip = make_gate(True)

    @guppy.unitary
    class apply[G: Unitary[[qubit], None]]:
        @guppy(unitary=True)
        def __call__(q: qubit, gate: G) -> None:
            gate(q)

        @guppy
        def controlled[n: nat](q: qubit, gate: G, controls: array[qubit, n]) -> None:
            with control(controls):
                gate(q)

    @guppy
    def main() -> int:
        flag, target = qubit(), qubit()
        x(flag)
        with control(flag):
            apply(target, identity)
            apply(target, flip)
        discard(flag)
        return int(measure(target).read())

    run_int_fn(main, expected=1, num_qubits=2)
