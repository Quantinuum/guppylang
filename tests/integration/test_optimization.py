"""Tests optimizing Hugrs generated offline by Guppy programs."""

# ALAN TODO Should be integrated into either tests/test_optimization.py
# or tests/integration/tket_opt/
from collections.abc import Callable
import pytest

from hugr.build.base import Hugr
from hugr.ops import AsExtOp
from hugr.package import Package
from tket._state import CompilationState
from tket.passes import PytketHugrPass, QSystemRebasePass, _QSystemLLVMPass
from guppylang import guppy
from guppylang.defs import GuppyFunctionDefinition
from guppylang.optimizer import OptimizationLevel
from guppylang.std.builtins import result, array, owned
from guppylang.std.quantum import cx, h, rx, cz, rz, measure, qubit
from guppylang.std.angles import angle

# Import the pytket passes, if the `pytket` extra has been installed.
# If not, skip all tests in this file.
pytket = pytest.importorskip("pytket")
from pytket.passes import CliffordSimp  # noqa: E402


def _count_gates(hugr: Hugr) -> dict[str, int]:
    """Returns mapping from qualified ID to count for gates and result ops only"""
    counts: dict[str, int] = {}
    for _, data in hugr.nodes():
        if isinstance(data.op, AsExtOp):
            op_name = data.op.op_def().qualified_name()
            if any(
                op_name.startswith(prefix)
                for prefix in ["tket.quantum.", "TKET1.", "tket.result."]
            ):
                counts[op_name] = counts.get(op_name, 0) + 1
    return counts


def _with_clifford_simp(func: GuppyFunctionDefinition):
    return func.with_opt_level(OptimizationLevel.Classical).with_optimization(
        PytketHugrPass(CliffordSimp(allow_swaps=True))
    )


def ranges_opt():
    @guppy
    def main() -> None:
        q1, q2, q3, q4 = qubit(), qubit(), qubit(), qubit()
        b1 = measure(q1)
        b2 = measure(q2)
        b3 = measure(q3)
        b4 = measure(q4)

        result("b1", b1.read())
        result("b2", b2.read())
        result("b3", b3.read())
        result("b4", b4.read())

    return main.compile()


def ranges_flat():
    @guppy
    def main() -> None:
        q1, q2, q3, q4 = qubit(), qubit(), qubit(), qubit()
        q1, q2, q3, q4 = f(array(q1, q2, q3, q4))
        b1 = measure(q1)
        b2 = measure(q2)
        b3 = measure(q3)
        b4 = measure(q4)

        result("b1", b1.read())
        result("b2", b2.read())
        result("b3", b3.read())
        result("b4", b4.read())

    @guppy.comptime
    def f(qs: array[qubit, 4] @ owned) -> array[qubit, 4]:
        for i in range(4):
            h(qs[(-i) % 4])
        for i in range(3):
            cx(qs[i], qs[i + 1])
        for i in range(3):
            cx(qs[2 - i], qs[3 - i])
        for i in range(4):
            h(qs[(3 * i + 1) % 4])
        return qs

    return main.compile()


def ranges():
    @guppy
    def main() -> None:
        q1, q2, q3, q4 = qubit(), qubit(), qubit(), qubit()
        q1, q2, q3, q4 = f(array(q1, q2, q3, q4))
        b1 = measure(q1)
        b2 = measure(q2)
        b3 = measure(q3)
        b4 = measure(q4)

        result("b1", b1.read())
        result("b2", b2.read())
        result("b3", b3.read())
        result("b4", b4.read())

    @guppy
    def f(qs: array[qubit, 4] @ owned) -> array[qubit, 4]:
        for i in range(4):
            h(qs[(-i) % 4])
        for i in range(3):
            cx(qs[i], qs[i + 1])
        for i in range(3):
            cx(qs[2 - i], qs[3 - i])
        for i in range(4):
            h(qs[(3 * i + 1) % 4])
        return qs

    return main.compile()


def ranges_flat_array():
    """Version of `ranges` with flattened control flow but retaining array accesses"""

    @guppy
    def main() -> None:
        q1, q2, q3, q4 = qubit(), qubit(), qubit(), qubit()
        q1, q2, q3, q4 = f(array(q1, q2, q3, q4))
        b1 = measure(q1)
        b2 = measure(q2)
        b3 = measure(q3)
        b4 = measure(q4)

        result("b1", b1.read())
        result("b2", b2.read())
        result("b3", b3.read())
        result("b4", b4.read())

    @guppy
    def f(qs: array[qubit, 4] @ owned) -> array[qubit, 4]:
        h(qs[0])
        h(qs[3])
        h(qs[2])
        h(qs[1])

        cx(qs[0], qs[1])
        cx(qs[1], qs[2])
        cx(qs[2], qs[3])

        cx(qs[2], qs[3])
        cx(qs[1], qs[2])
        cx(qs[0], qs[1])

        h(qs[1])
        h(qs[0])
        h(qs[3])
        h(qs[2])
        return qs

    return main.compile()


def false_branch():
    @guppy
    def main() -> None:
        q = qubit()
        h(q)
        if True:
            h(q)
        if False:
            h(q)
        b = measure(q).read()

        result("b", b)

    return main.compile()


def false_branch_opt():
    @guppy
    def main() -> None:
        result("b", 0)

    return main.compile()


def nested_array():
    @guppy
    def main(arr: array[array[qubit, 5], 3]) -> None:
        cx(arr[0][1], arr[0][2])
        cx(arr[0][1], arr[0][2])

    return main.compile_function()


def nested_array_opt():
    @guppy
    def main(arr: array[array[qubit, 5], 3]) -> None:
        # it may be impossible to elide the three borrow/return pairs
        # of different indices in case these panic...so something like
        # def inner(ar: array[qubit, 5]) -> None:
        #    inner2(ar[1], ar[2])
        # def inner2(q1: qubit, q2: qubit) -> None:
        #    pass
        # inner(ar[0])
        pass

    return main.compile_function()


def func_decls():
    @guppy.declare
    def func1() -> float: ...

    @guppy.declare
    def func2(f: float, q: qubit) -> float: ...

    @guppy
    def unknown_rotations(q: qubit) -> None:
        rotation = func1()
        rx(q, angle(rotation))

        # Some operations that we can optimize away.
        h(q)
        h(q)

        other_rotation = func2(rotation + 1.0, q)
        rx(q, angle(other_rotation))

    return unknown_rotations.compile_function()


def func_decls_flat():
    @guppy.declare
    def func1() -> float: ...

    @guppy.declare
    def func2(f: float, q: qubit) -> float: ...

    @guppy.comptime
    def unknown_rotations(q: qubit) -> None:
        rotation = func1()
        rx(q, angle(rotation))

        # Some operations that we can optimize away.
        h(q)
        h(q)

        other_rotation = func2(rotation + 1.0, q)
        rx(q, angle(other_rotation))

    return unknown_rotations.compile_function()


def func_decls_opt():
    @guppy.declare
    def func1() -> float: ...

    @guppy.declare
    def func2(f: float, q: qubit) -> float: ...

    @guppy
    def unknown_rotations(q: qubit) -> None:
        rotation = func1()
        rx(q, angle(rotation))

        other_rotation = func2(rotation + 1.0, q)
        rx(q, angle(other_rotation))

    return unknown_rotations.compile_function()


def simple_cx_opt():
    @guppy
    def main() -> None:
        result("b1", 0)
        result("b2", 0)

    return main.compile()


def simple_cx():
    @guppy
    def main() -> None:
        q1, q2 = qubit(), qubit()
        cx(q1, q2)
        cx(q1, q2)
        b1 = measure(q1)
        b2 = measure(q2)

        result("b1", b1.read())
        result("b2", b2.read())

    return main.compile()


def nested_flat():
    @guppy
    def main() -> None:
        q1, q2, q3 = qubit(), qubit(), qubit()
        q1, q2, q3 = f(array(q1, q2, q3))
        b1 = measure(q1)
        b2 = measure(q2)
        b3 = measure(q3)

        result("b1", b1.read())
        result("b2", b2.read())
        result("b3", b3.read())

    @guppy.comptime
    def f(qs: array[qubit, 3] @ owned) -> array[qubit, 3]:
        for i in range(3):
            h(qs[i])
        for i in range(2):
            for j in range(3):
                cz(qs[j], qs[(j + 1) % 3])
        for i in range(3):
            h(qs[i])
        return qs

    # OptimizationLevel.Default includes only RemoveRedundanciesPass
    # which is not sufficient here.
    return _with_clifford_simp(main).compile()


def nested_opt():
    @guppy
    def main() -> None:
        q1, q2, q3 = qubit(), qubit(), qubit()
        b1 = measure(q1)
        b2 = measure(q2)
        b3 = measure(q3)

        result("b1", b1.read())
        result("b2", b2.read())
        result("b3", b3.read())

    return main.compile()


def nested():
    @guppy
    def main() -> None:
        q1, q2, q3 = qubit(), qubit(), qubit()
        q1, q2, q3 = f(array(q1, q2, q3))
        b1 = measure(q1)
        b2 = measure(q2)
        b3 = measure(q3)

        result("b1", b1.read())
        result("b2", b2.read())
        result("b3", b3.read())

    @guppy
    def f(qs: array[qubit, 3] @ owned) -> array[qubit, 3]:
        for i in range(3):
            h(qs[i])
        for i in range(2):
            for j in range(3):
                cz(qs[j], qs[(j + 1) % 3])
        for i in range(3):
            h(qs[i])
        return qs

    # This still doesn't optimize even with CliffordSimp, so this achieves
    # nothing currently. However `nested_flat` is optimized only with CliffordSimp
    # so use that here too.
    return _with_clifford_simp(main).compile()


def angles():
    """Some angle logic that reduces to the identity.

    This may be harder to optimize, as it requires const-folding angles through loop
    unpeeling.
    """

    @guppy
    def main() -> None:
        q = qubit()
        q = f(q)
        b = measure(q)

        result("b", b.read())

    @guppy
    def g(q: qubit, x: angle) -> None:
        rz(q, x / 2 - angle(0.1))
        rz(q, x / 2 + angle(0.1))

    @guppy
    def f(q: qubit @ owned) -> qubit:
        h(q)
        x: angle = angle(0.0)
        for i in range(5):
            g(q, x)
            x += angle(0.2)
        h(q)
        return q

    return main.compile()


def angles_opt():
    @guppy
    def main() -> None:
        result("b", 0)

    return main.compile()


def angles_flat(lvl: OptimizationLevel | None = None):
    @guppy
    def main() -> None:
        q = qubit()
        q = f(q)
        b = measure(q)

        result("b", b.read())

    @guppy.comptime
    def g(q: qubit, x: angle) -> None:
        rz(q, x / 2 - angle(0.1))
        rz(q, x / 2 + angle(0.1))

    @guppy.comptime
    def f(q: qubit @ owned) -> qubit:
        h(q)
        x: angle = angle(0.0)
        for i in range(5):
            g(q, x)
            x += angle(0.2)
        h(q)
        return q

    return (main if lvl is None else main.with_opt_level(lvl)).compile()


def test_angles_rotations() -> None:
    def count_from_halfturns(hugr: Hugr) -> int:
        return sum(
            int(data.op.name().startswith("tket.rotation.from_halfturns"))
            for _, data in hugr.nodes()
        )

    hugr = angles_flat(OptimizationLevel.Minimal).modules[0]
    # No function inlining yet, so only two rotations, in g().
    assert count_from_halfturns(hugr) == 2

    # Recompile with default optimization.
    hugr = angles_flat().modules[0]

    optimized = angles_opt().modules[0]
    assert count_from_halfturns(optimized) == 0
    assert count_from_halfturns(hugr) == 10
    pytest.xfail("https://github.com/Quantinuum/tket2/issues/2126")


def test_optimize_ranges_array() -> None:
    """Demonstrates we can fully optimize the array operations in ranges.

    (i.e. after control flow is flattened, but the array ops are not)"""

    hugr = ranges_flat_array().modules[0]

    expected_counts = _count_gates(ranges_opt().modules[0])
    assert _count_gates(hugr) == expected_counts


@pytest.mark.parametrize(
    ("original", "flattened", "optimized", "expected"),
    [
        (nested_array, None, nested_array_opt, None),  # There is no nested_array_flat
        (
            angles_flat,
            None,
            angles_opt,
            {
                "tket.quantum.MeasureFree": 1,
                "tket.quantum.QAlloc": 1,
                "tket.result.result_bool": 1,
            },
        ),  # Since "flat" fails, do not bother testing "original"
        (
            simple_cx,
            None,  # There is no flat
            simple_cx_opt,
            {
                "tket.quantum.QAlloc": 2,
                "tket.quantum.MeasureFree": 2,
                "tket.result.result_bool": 2,
            },
        ),
        (nested_flat, None, nested_opt, None),
        (
            nested,
            None,  # Does not flatten properly
            nested_opt,
            {
                "tket.quantum.QAlloc": 3,
                "tket.quantum.MeasureFree": 3,
                "tket.result.result_bool": 3,
                "TKET1.tk1op": 4,
                "tket.quantum.CX": 1,
            },
        ),
        (ranges_flat, None, ranges_opt, None),
        (
            ranges,
            None,  # Does not flatten properly
            ranges_opt,
            {
                "tket.quantum.QAlloc": 4,
                "tket.quantum.MeasureFree": 4,
                "tket.result.result_bool": 4,
                "tket.quantum.H": 2,  # Would be TKET1.tk1op if we used CliffordSimp
                "tket.quantum.CX": 2,
            },
        ),
        (
            false_branch,
            None,  # There is no false_branch_flat
            false_branch_opt,
            {
                "tket.quantum.QAlloc": 1,
                "tket.quantum.MeasureFree": 1,
                "tket.result.result_bool": 1,
            },
        ),
        (
            func_decls,
            func_decls_flat,
            func_decls_opt,
            None,
        ),  # Note special-casing of optimizations applied
    ],
)
def test_optimize(
    original: Callable[[], Package],
    flattened: Callable[[], Package] | None,
    optimized: Callable[[], Package],
    expected: dict[str, int] | None,
) -> None:
    """Test full optimization pipeline on Guppy circuits.

    Check that each example optimizes to the full extent given by the .opt .hugr files,
    including lowering to QSystem.
    """
    hugr = original().modules[0]
    actual_counts = _count_gates(hugr)

    if flattened is not None:
        flat_counts = _count_gates(flattened().modules[0])
        assert actual_counts == flat_counts

    optimized_counts = _count_gates(optimized().modules[0])

    QSystemRebasePass().run(hugr)
    _QSystemLLVMPass().run(hugr)

    CompilationState.from_python(hugr).validate()

    if expected is not None:
        assert actual_counts != optimized_counts
        assert actual_counts == expected
        pytest.xfail()
    else:
        assert actual_counts == optimized_counts
