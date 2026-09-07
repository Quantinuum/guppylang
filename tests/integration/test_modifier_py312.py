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
from guppylang.std.quantum import h, qubit


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
