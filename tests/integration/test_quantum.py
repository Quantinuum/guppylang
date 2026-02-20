"""Various tests for the functions defined in `guppylang.prelude.quantum`."""

from typing import no_type_check

from guppylang.std.angles import angle

from guppylang.std.builtins import owned, array, panic, result
from guppylang.std.platform import barrier


from guppylang.std import quantum as q
from guppylang.std.quantum import (
    discard,
    measure,
    qubit,
    maybe_qubit,
    measure_array,
    discard_array,
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


def test_alloc(validate):
    @guppy
    def test() -> tuple[bool, bool]:
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
    def test(q1: qubit @ owned, q2: qubit @ owned) -> tuple[bool, bool]:
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
    def test() -> array[bool, 10]:
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


def test_1qb_op_array(validate):
    """Apply single-qubit gates to arrays of qubits."""

    @guppy
    @no_type_check
    def test() -> None:
        qs = array(qubit() for _ in range(5))
        q.h(qs)
        q.t(qs)
        q.s(qs)
        q.v(qs)
        q.x(qs)
        q.y(qs)
        q.z(qs)
        q.tdg(qs)
        q.sdg(qs)
        q.vdg(qs)
        q.reset(qs)
        discard_array(qs)

    validate(test.compile_function())


def test_2qb_op_array(validate):
    """Apply two-qubit gates to arrays of qubits."""

    @guppy
    @no_type_check
    def test() -> None:
        qs1 = array(qubit() for _ in range(5))
        qs2 = array(qubit() for _ in range(5))
        q.cx(qs1, qs2)
        q.cy(qs1, qs2)
        q.cz(qs1, qs2)
        discard_array(qs1)
        discard_array(qs2)

    validate(test.compile_function())


def test_measure_overload(validate):
    """Measure an array of qubits using the overloaded measure function."""

    @guppy
    def test() -> array[bool, 10]:
        qs = array(qubit() for _ in range(10))
        return measure(qs)

    validate(test.compile_function())


def test_discard_overload(validate):
    """Discard an array of qubits using the overloaded discard function."""

    @guppy
    def test() -> None:
        qs = array(qubit() for _ in range(10))
        discard(qs)

    validate(test.compile_function())


def test_functional_1qb_array(validate):
    """Functional single-qubit gates on arrays."""

    @guppy
    def test() -> array[bool, 5]:
        qs = array(qubit() for _ in range(5))
        qs = h(qs)
        qs = x(qs)
        qs = z(qs)
        return measure(qs)

    validate(test.compile_function())


def test_functional_2qb_array(validate):
    """Functional two-qubit gates on arrays."""

    @guppy
    def test() -> None:
        qs1 = array(qubit() for _ in range(5))
        qs2 = array(qubit() for _ in range(5))
        qs1, qs2 = cx(qs1, qs2)
        qs1, qs2 = cy(qs1, qs2)
        qs1, qs2 = cz(qs1, qs2)
        discard(qs1)
        discard(qs2)

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

        result("c", x)
        result("c2", measure(q1))

    validate(test.compile_function())
