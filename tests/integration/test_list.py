import pytest
from guppylang import qubit, guppy
from guppylang.std.angles import angle
from guppylang.std.builtins import owned
from guppylang.std.quantum import cx, rz
from guppylang.std.quantum.functional import h

from tests.util import compile_guppy


def test_types(validate):
    @compile_guppy
    def test(
        xs: list[int], ys: list[tuple[int, float]]
    ) -> tuple[list[int], list[tuple[int, float]]]:
        return xs, ys

    validate(test)


def test_len(validate):
    @compile_guppy
    def test(xs: list[int]) -> int:
        return len(xs)

    validate(test)


def test_literal(validate):
    @compile_guppy
    def test(x: float) -> list[float]:
        return [1.0, 2.0, 3.0, 4.0 + x]

    validate(test)


def test_literal_linear(validate):
    @guppy
    def test(q1: qubit @ owned, q2: qubit @ owned) -> list[qubit]:
        return [q1, h(q2)]

    validate(test.compile_function())


def test_push_pop(validate):
    @compile_guppy
    def test(xs: list[int]) -> bool:
        xs.append(3)
        x = xs.pop()
        return x == 3

    validate(test)


@pytest.mark.skip("See https://github.com/quantinuum/guppylang/issues/528")
def test_arith(validate):
    @compile_guppy
    def test(xs: list[int]) -> list[int]:
        xs += xs + [42]
        xs = 3 * xs
        return xs * 4

    validate(test)


@pytest.mark.skip("See https://github.com/quantinuum/guppylang/issues/528")
def test_arith_linear(validate):
    @guppy
    def test(
        xs: list[qubit] @ owned, ys: list[qubit] @ owned, q: qubit @ owned
    ) -> list[qubit]:
        xs += [q]
        return xs + ys

    validate(test.compile_function())


def test_subscript(validate):
    @compile_guppy
    def test(xs: list[float], i: int) -> float:
        return xs[2 * i]

    validate(test)


def test_linear(validate):
    @guppy
    def test(xs: list[qubit], q: qubit @ owned) -> int:
        xs.append(q)
        return len(xs)

    validate(test.compile_function())


def test_subscript_drop_rest(validate):
    @guppy.declare
    def foo() -> list[int]: ...

    @guppy
    def main() -> int:
        return foo()[0]

    validate(main.compile_function())


def test_linear_subscript(validate):
    @guppy.declare
    def foo(q: qubit) -> None: ...

    @guppy
    def main(qs: list[qubit] @ owned, i: int) -> list[qubit]:
        foo(qs[i])
        return qs

    validate(main.compile_function())


def test_inout_subscript(validate):
    @guppy.declare
    def foo(q: qubit) -> None: ...

    @guppy
    def main(qs: list[qubit], i: int) -> None:
        foo(qs[i])

    validate(main.compile_function())


def test_multi_subscripts(validate):
    @guppy.declare
    def foo(q1: qubit, q2: qubit) -> None: ...

    @guppy
    def main(qs: list[qubit] @ owned) -> list[qubit]:
        foo(qs[0], qs[1])
        # Note: `foo(qs[0], qs[0])` is rejected at compile time
        i = 0
        foo(qs[i], qs[i])  # Will panic at runtime
        return qs

    validate(main.compile_function())


def test_struct_list(validate):
    @guppy.struct
    class S:
        q1: qubit
        q2: qubit

    @guppy.declare
    def foo(q1: qubit, q2: qubit) -> None: ...

    @guppy
    def main(ss: list[S] @ owned) -> list[S]:
        # This will panic at runtime :(
        # To make this work, we would need to replace the qubits in the struct
        # with `qubit | None` and write back `None` after `q1` has been extracted...
        foo(ss[0].q1, ss[0].q2)
        return ss

    validate(main.compile_function())


def test_nested_subscripts(validate):
    @guppy.declare
    def foo(q: qubit) -> None: ...

    @guppy.declare
    def bar(q1: qubit, q2: qubit, q3: qubit, q4: qubit) -> None: ...

    @guppy
    def main(qs: list[list[qubit]] @ owned) -> list[list[qubit]]:
        foo(qs[0][0])
        # The following should work *without* panicking at runtime! Accessing `qs[0][0]`
        # replaces one qubit with `None` but puts everything back into `qs` before
        # going to the next argument.
        bar(qs[0][0], qs[0][1], qs[1][0], qs[1][1])
        return qs

    validate(main.compile_function())


def test_struct_nested_subscript(validate):
    @guppy.struct
    class C:
        c: qubit
        blah: int

    @guppy.struct
    class B:
        ys: list[list[C]]
        foo: C

    @guppy.struct
    class A:
        xs: list[B]
        bar: qubit
        baz: tuple[B, B]

    @guppy.declare
    def foo(q1: qubit) -> None: ...

    @guppy
    def main(a: A @ owned, i: int, j: int, k: int) -> A:
        foo(a.xs[i].ys[j][k].c)
        return a

    validate(main.compile_function())


def test_phase_gadget(validate):
    @guppy
    def paulig(qs: list[qubit], alpha: angle) -> None:
        n = len(qs)
        for i in range(n - 1):
            cx(qs[i], qs[i + 1])
        rz(qs[n - 1], alpha)
        for i in range(n - 1):
            cx(qs[n - i - 1], qs[n - i - 2])

    validate(paulig.compile_function())
