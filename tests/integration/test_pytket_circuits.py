"""Tests for loading pytket circuits as functions."""

from guppylang.decorator import guppy
from guppylang.std.angles import angle, pi
from guppylang.std.quantum import qubit, discard_array, discard, measure
from guppylang.std.builtins import array, result
from pytket import Circuit, OpType
from pytket.passes import AutoRebase
from sympy import Symbol, sympify


def test_single_qubit_circuit(validate):
    circ = Circuit(1)
    circ.H(0)

    @guppy.pytket(circ)
    def guppy_circ(q1: qubit) -> None: ...

    @guppy
    def foo(q: qubit) -> None:
        guppy_circ(q)

    validate(foo.compile_function())


def test_multi_qubit_circuit(validate):
    circ = Circuit(2)
    circ.H(0)
    circ.CX(0, 1)

    @guppy.pytket(circ)
    def guppy_circ(q1: qubit, q2: qubit) -> None: ...

    @guppy
    def foo(q1: qubit, q2: qubit) -> None:
        guppy_circ(q1, q2)

    validate(foo.compile_function())


def test_measure(validate):
    circ = Circuit(1)
    circ.H(0)
    circ.measure_all()

    @guppy.pytket(circ)
    def guppy_circ(q: qubit) -> bool: ...

    @guppy
    def foo(q: qubit) -> bool:
        return guppy_circ(q)

    validate(foo.compile_function())


def test_measure_multiple(validate):
    circ = Circuit(2, 2)
    circ.H(0)
    circ.measure_all()

    @guppy.pytket(circ)
    def guppy_circ(q1: qubit, q2: qubit) -> tuple[bool, bool]: ...

    @guppy
    def foo(q1: qubit, q2: qubit) -> tuple[bool, bool]:
        return guppy_circ(q1, q2)

    validate(foo.compile_function())


def test_measure_not_last(validate):
    circ = Circuit(1, 1)
    circ.H(0)
    circ.measure_all()
    circ.X(0)

    @guppy.pytket(circ)
    def guppy_circ(q: qubit) -> bool: ...

    @guppy
    def foo(q: qubit) -> bool:
        return guppy_circ(q)

    validate(foo.compile_function())


def test_load_circuit(validate):
    circ = Circuit(1)
    circ.H(0)

    guppy_circ = guppy.load_pytket("guppy_circ", circ, use_arrays=False)

    @guppy
    def foo(q: qubit) -> None:
        guppy_circ(q)

    validate(foo.compile_function())


def test_load_circuits(validate):
    circ1 = Circuit(1)
    circ1.H(0)

    circ2 = Circuit(2)
    circ2.CX(0, 1)
    circ2.measure_all()

    guppy_circ1 = guppy.load_pytket("guppy_circ1", circ1, use_arrays=False)
    guppy_circ2 = guppy.load_pytket("guppy_circ2", circ2, use_arrays=False)

    @guppy
    def foo(q1: qubit, q2: qubit, q3: qubit) -> tuple[bool, bool]:
        guppy_circ1(q1)
        return guppy_circ2(q2, q3)

    validate(foo.compile_function())


def test_measure_some(validate):
    circ = Circuit(2, 1)
    circ.CX(0, 1)
    circ.Measure(0, 0)

    guppy_circ = guppy.load_pytket("guppy_circ", circ, use_arrays=False)

    @guppy
    def foo(q1: qubit, q2: qubit) -> bool:
        return guppy_circ(q1, q2)

    validate(foo.compile_function())


def test_register_arrays_default(validate):
    circ = Circuit(2)

    guppy_circ = guppy.load_pytket("guppy_circ", circ)

    @guppy
    def foo(default_reg: array[qubit, 2]) -> None:
        return guppy_circ(default_reg)

    validate(foo.compile_function())


def test_register_arrays(validate):
    circ = Circuit(2)
    reg = circ.add_q_register("extra_reg", 3)
    circ.measure_register(reg, "extra_bits")

    guppy_circ = guppy.load_pytket("guppy_circ", circ)

    @guppy
    def foo(default_reg: array[qubit, 2], extra_reg: array[qubit, 3]) -> array[bool, 3]:
        # Note that the default_reg name is 'q' so it has to come after 'e...'
        # lexicographically.
        return guppy_circ(extra_reg, default_reg)

    validate(foo.compile_function())


def test_register_arrays_multiple_measure(validate):
    circ = Circuit(2)
    reg1 = circ.add_q_register("extra_reg1", 3)
    reg2 = circ.add_q_register("extra_reg2", 2)
    circ.measure_register(reg1, "extra_bits1")
    circ.measure_register(reg2, "extra_bits2")

    guppy_circ = guppy.load_pytket("guppy_circ", circ)

    @guppy
    def foo(
        default_reg: array[qubit, 2], extra_reg1: array[qubit, 3]
    ) -> tuple[array[bool, 3], array[bool, 2]]:
        extra_reg2 = array(qubit(), qubit())
        result = guppy_circ(extra_reg1, extra_reg2, default_reg)
        # Until we add linearity checks to loaded circuits need to discard owned
        # arrays.
        discard_array(extra_reg2)
        return result

    validate(foo.compile_function())


def test_register_arrays_mixed(validate):
    circ = Circuit(2, 1)
    reg = circ.add_q_register("q2", 3)
    circ.measure_register(reg, "c2")
    circ.Measure(0, 0)

    guppy_circ = guppy.load_pytket("guppy_circ", circ)

    @guppy
    def foo(
        q: array[qubit, 2], q2: array[qubit, 3]
    ) -> tuple[array[bool, 1], array[bool, 3]]:
        return guppy_circ(q, q2)

    validate(foo.compile_function())


def test_compile_sig(validate):
    circ = Circuit(1)
    circ.H(0)

    @guppy.pytket(circ)
    def guppy_circ(q1: qubit) -> None: ...

    validate(guppy_circ.compile_function())


def test_compile_load(validate):
    circ = Circuit(1)
    circ.H(0)

    pytket_func = guppy.load_pytket("guppy_circ", circ, use_arrays=False)

    validate(pytket_func.compile_function())


def test_symbolic(validate):
    a = Symbol("alpha")
    b = Symbol("beta")

    circ = Circuit(2)
    circ.YYPhase(b, 0, 1)
    circ.Rx(a, 0)
    circ.measure_all()

    AutoRebase({OpType.CX, OpType.Rz, OpType.H}).apply(circ)

    guppy_circ = guppy.load_pytket("guppy_circ", circ, use_arrays=False)

    @guppy
    def foo(q1: qubit, q2: qubit) -> tuple[bool, bool]:
        alpha = angle(0.3)
        beta = angle(1.2)
        return guppy_circ(q1, q2, alpha, beta)

    validate(foo.compile_function())


def test_symbolic_array(validate):
    a = Symbol("alpha")
    b = Symbol("beta")

    circ = Circuit(3)
    circ.YYPhase(b, 0, 1)
    circ.Rx(a, 0)
    circ.measure_all()

    AutoRebase({OpType.CX, OpType.Rz, OpType.H}).apply(circ)

    guppy_circ = guppy.load_pytket("guppy_circ", circ)

    @guppy
    def foo(reg: array[qubit, 3]) -> array[bool, 3]:
        params = array(angle(0.3), angle(1.2))
        return guppy_circ(reg, params)

    validate(foo.compile_function())


def test_symbolic_exec(validate, run_int_fn):
    a = Symbol("alpha")

    circ = Circuit(1)
    circ.Rx(a, 0)
    circ.measure_all()

    AutoRebase({OpType.CX, OpType.Rz, OpType.H}).apply(circ)

    flip = guppy.load_pytket("flip", circ, use_arrays=False)

    @guppy
    def main() -> int:
        q = qubit()
        res = int(flip(q, pi))
        discard(q)
        return res

    validate(main.compile_function())
    run_int_fn(main, 1, num_qubits=2)


def test_exec(validate, run_int_fn):
    circ = Circuit(2, 2)
    circ.X(0)
    circ.measure_all()

    guppy_circ = guppy.load_pytket("guppy_circ", circ, use_arrays=False)

    @guppy
    def foo(q1: qubit, q2: qubit) -> tuple[bool, bool]:
        res = guppy_circ(q1, q2)
        return res

    @guppy
    def main() -> int:
        q1 = qubit()
        q2 = qubit()
        res = foo(q1, q2)
        discard(q1)
        discard(q2)
        return int(res[0])

    validate(main.compile_function())
    run_int_fn(main, 1, num_qubits=2)


def test_qsystem_ops(validate):
    circ = Circuit(2)
    circ.PhasedX(angle0=0.5, angle1=0.2, qubit=0)
    circ.ZZPhase(angle=0.3, qubit0=0, qubit1=1)
    circ.ZZMax(qubit0=1, qubit1=0)

    @guppy.pytket(circ)
    def guppy_circ(q1: qubit, q2: qubit) -> None: ...

    @guppy
    def foo(q1: qubit, q2: qubit) -> None:
        guppy_circ(q1, q2)

    compiled = foo.compile_function()
    validate(compiled)

    # Assert that we have no opaque (unrecognised) tket1 operations
    hugr = compiled.modules[0]
    for node in hugr.descendants(hugr.module_root):
        op_name = hugr[node].op.name()
        assert "tk1op" not in op_name


def test_qsystem_exec():
    circ = Circuit(2)
    circ.H(0)
    circ.H(1)

    # Full rotation, just an identity
    # ZZMax() ∘ ZZPhase(-7/2) = ZZPhase(-4) = I
    circ.ZZMax(qubit0=1, qubit1=0)
    circ.ZZPhase(angle=sympify("(7/2)"), qubit0=0, qubit1=1)
    # Another id operation
    # PhasedX(2, -1/3) = I
    circ.PhasedX(
        angle0=sympify("(3/2) / 3 - (-3 * 1/2)"),
        angle1=sympify("-(1/3)"),
        qubit=0,
    )
    # And again
    # Rz(𝜋/2) ∘ Rz(-𝜋/2) = I
    circ.Rz(angle=sympify("(pi/2)"), qubit=0)
    circ.Rz(angle=sympify("(-pi/2)"), qubit=0)

    circ.H(0)
    circ.H(1)

    @guppy.pytket(circ)
    def guppy_circ(q1: qubit, q2: qubit) -> None: ...

    @guppy
    def main() -> None:
        a, b = qubit(), qubit()

        guppy_circ(a, b)

        result("a", measure(a))
        result("b", measure(b))

    # deterministic - should always be 0
    res = main.emulator(n_qubits=2).run()
    for r in res.results:
        assert r.entries == [("a", 0), ("b", 0)]
