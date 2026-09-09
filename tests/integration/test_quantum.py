"""Various tests for the functions defined in `guppylang.prelude.quantum`."""

from typing import Self, no_type_check

from guppylang.std.angles import angle

from guppylang.std.builtins import owned, array, panic, output
from guppylang.std.platform import barrier

from guppylang.std import quantum as q
from guppylang.std.quantum import (
    discard,
    measure,
    qubit,
    maybe_qubit,
    measure_array,
    discard_array,
    Measurement,
    AbstractQubit,
)
from guppylang.std.quantum.functional import (
    cx,
    cy,
    cz,
    h,
    t,
    s,
    v,
    x,
    y,
    z,
    tdg,
    sdg,
    vdg,
    rx,
    ry,
    rz,
    crz,
    ch,
    toffoli,
    reset,
    project_z,
)

from tests.util import guppy


def test_abstract_qubit(validate):
    @guppy.struct
    class WrappedQubit:
        inner: qubit

        @guppy(unitary=True)
        def hadamard(self) -> None:
            q.h(self.inner)

        @guppy(unitary=True)
        def controlled_z(self, target: Self) -> None:
            q.cz(self.inner, target.inner)

        @guppy(unitary=True)
        def controlled_y(self, target: Self) -> None:
            q.cy(self.inner, target.inner)

        @guppy(unitary=True)
        def controlled_x(self, target: Self) -> None:
            q.cx(self.inner, target.inner)

        @guppy(unitary=True)
        def phase_t(self) -> None:
            q.t(self.inner)

        @guppy(unitary=True)
        def phase_s(self) -> None:
            q.s(self.inner)

        @guppy(unitary=True)
        def sqrt_x(self) -> None:
            q.v(self.inner)

        @guppy(unitary=True)
        def pauli_x(self) -> None:
            q.x(self.inner)

        @guppy(unitary=True)
        def pauli_y(self) -> None:
            q.y(self.inner)

        @guppy(unitary=True)
        def pauli_z(self) -> None:
            q.z(self.inner)

        @guppy(unitary=True)
        def phase_t_dagger(self) -> None:
            q.tdg(self.inner)

        @guppy(unitary=True)
        def phase_s_dagger(self) -> None:
            q.sdg(self.inner)

        @guppy(unitary=True)
        def sqrt_x_dagger(self) -> None:
            q.vdg(self.inner)

        @guppy(unitary=True)
        def rotate_z(self, theta: angle) -> None:
            q.rz(self.inner, theta)

        @guppy(unitary=True)
        def rotate_x(self, theta: angle) -> None:
            q.rx(self.inner, theta)

        @guppy(unitary=True)
        def rotate_y(self, theta: angle) -> None:
            q.ry(self.inner, theta)

        @guppy(unitary=True)
        def controlled_rotate_z(self, target: Self, theta: angle) -> None:
            q.crz(self.inner, target.inner, theta)

        @guppy(unitary=True)
        def toffoli(self, control2: Self, target: Self) -> None:
            q.toffoli(self.inner, control2.inner, target.inner)

        @guppy(unitary=True)
        def controlled_hadamard(self, target: Self) -> None:
            q.ch(self.inner, target.inner)

        @guppy
        def measure(self: Self @ owned) -> Measurement:
            return q.measure(self.inner)

        @guppy
        def project_z(self) -> Measurement:
            return q.project_z(self.inner)

        @guppy
        def discard(self: Self @ owned) -> None:
            q.discard(self.inner)

        @guppy
        def reset(self) -> None:
            q.reset(self.inner)

    @guppy
    def use[Q: AbstractQubit](q1: Q @ owned, q2: Q @ owned) -> tuple[Q, Q]:
        q.h(q1)
        q.cx(q1, q2)
        q.ry(q1, angle(0.5))
        q1, q2 = cx(q1, q2)
        return q1, q2

    @guppy
    def test() -> tuple[WrappedQubit, WrappedQubit]:
        return use(WrappedQubit(qubit()), WrappedQubit(qubit()))

    validate(test.compile_function())


def test_alloc(validate):
    @guppy
    def test() -> tuple[Measurement, Measurement]:
        q1, q2 = qubit(), maybe_qubit().unwrap()
        q1, q2 = cx(q1, q2)
        return (measure(q1), measure(q2))

    validate(test.compile_function())


def test_1qb_op(validate):
    @guppy
    def test(q: qubit @ owned) -> qubit:
        q = h(q)
        q = t(q)
        q = s(q)
        q = v(q)
        q = x(q)
        q = y(q)
        q = z(q)
        q = tdg(q)
        q = sdg(q)
        q = vdg(q)
        return q

    validate(test.compile_function())


def test_2qb_op(validate):
    @guppy
    def test(q1: qubit @ owned, q2: qubit @ owned) -> tuple[qubit, qubit]:
        q1, q2 = cx(q1, q2)
        q1, q2 = cy(q1, q2)
        q1, q2 = cz(q1, q2)
        q1, q2 = ch(q1, q2)
        return (q1, q2)

    validate(test.compile_function())


def test_3qb_op(validate):
    @guppy
    def test(
        q1: qubit @ owned, q2: qubit @ owned, q3: qubit @ owned
    ) -> tuple[qubit, qubit, qubit]:
        q1, q2, q3 = toffoli(q1, q2, q3)
        return (q1, q2, q3)

    validate(test.compile_function())


def test_measure_ops(validate):
    """Compile various measurement-related operations."""

    @guppy
    def test(q1: qubit @ owned, q2: qubit @ owned) -> tuple[Measurement, Measurement]:
        q1, b1 = project_z(q1)
        q1 = discard(q1)
        q2 = reset(q2)
        b2 = measure(q2)
        return (b1, b2)

    validate(test.compile_function())


def test_parametric(validate):
    """Compile various parametric operations."""

    @guppy
    def test(
        q1: qubit @ owned, q2: qubit @ owned, a1: angle, a2: angle, a3: angle
    ) -> tuple[qubit, qubit]:
        q1 = rx(q1, a1)
        q1 = ry(q1, a1)
        q2 = rz(q2, a3)
        q1, q2 = crz(q1, q2, a3)
        return (q1, q2)


def test_measure_array(validate):
    """Build and measure array."""

    @guppy
    def test() -> array[Measurement, 10]:
        qs = array(qubit() for _ in range(10))
        return measure_array(qs)

    validate(test.compile_function())


def test_discard_array(validate):
    """Build and discard array."""

    @guppy
    def test() -> None:
        qs = array(qubit() for _ in range(10))
        discard_array(qs)

    validate(test.compile_function())


def test_panic_discard(validate):
    """Panic while discarding qubit."""

    @guppy
    @no_type_check
    def test() -> None:
        q = qubit()
        panic("I panicked!", q)

    validate(test.compile_function())


def test_barrier(validate):
    """Barrier between ops."""

    @guppy
    @no_type_check
    def test() -> None:
        q1, q2, q3, q4 = qubit(), qubit(), qubit(), qubit()

        q.h(q1)
        q.h(q2)
        barrier(q1, q2, q3)
        q.h(q3)

        q.cx(q1, q2)
        barrier(q2, q3)
        q.cx(q3, q4)

        discard(q1)
        discard(q2)
        barrier()  # does nothing
        discard(q3)
        discard(q4)

    validate(test.compile_function())


def test_barrier_array(validate):
    """Barrier on array/struct access."""

    @guppy
    @no_type_check
    def test() -> None:
        qs = array(qubit() for _ in range(4))
        q.h(qs[0])
        q.h(qs[1])
        barrier(qs[0], qs[1], qs[2])
        barrier(qs[0])
        q.h(qs[2])

        q.cx(qs[0], qs[1])
        barrier(qs[1], qs[2])
        q.cx(qs[2], qs[3])
        barrier(qs)
        discard_array(qs)

    validate(test.compile_function())


def test_barrier_struct(validate):
    """Barrier on array/struct access."""

    @guppy.struct
    class S:
        q1: qubit
        q2: qubit
        q3: qubit
        q4: qubit

    @guppy
    @no_type_check
    def test() -> None:
        qs = S(qubit(), qubit(), qubit(), qubit())
        q.h(qs.q1)
        q.h(qs.q2)
        barrier(qs.q1, qs.q2, qs.q3)
        barrier(qs.q1)
        q.h(qs.q3)

        q.cx(qs.q1, qs.q2)
        barrier(qs.q2, qs.q3)
        q.cx(qs.q3, qs.q4)

        discard(qs.q1)
        discard(qs.q2)
        discard(qs.q3)
        discard(qs.q4)

    validate(test.compile_function())


def test_barrier_misc(validate):
    """Barrier on classical and non-place."""

    @guppy
    @no_type_check
    def test() -> None:
        q1 = qubit()
        q.h(q1)
        x = 1
        barrier(q1, array(1, 2, 3), 2 + 3, x)

        output("c", x)
        output("c2", measure(q1).read())

    validate(test.compile_function())
