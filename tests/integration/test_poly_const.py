from collections.abc import Callable
from typing import Generic

import pytest
from hugr import Hugr, ops

from guppylang import guppy, array, comptime
from guppylang.std.num import nat


def funcs_defs(h: Hugr) -> list[str]:
    return [h[node].op.f_name for node in h if isinstance(h[node].op, ops.FuncDefn)]


def test_bool(validate, run_int_fn):
    B = guppy.const_var("B", "bool")

    @guppy.struct
    class Dummy(Generic[B]):
        """Unit struct type to introduce generic B into the signature of `foo` below.

        This is needed because we don't support the `def foo[B: bool]` syntax yet to
        introduce type params that are not referenced in the signature.
        """

    @guppy
    def foo(_: Dummy[B]) -> bool:
        return B

    @guppy
    def main() -> int:
        s = 0
        if foo[True](Dummy()):
            s += 1
        if foo[False](Dummy()):
            s += 10
        if foo[True](Dummy()):
            s += 100
        if foo[False](Dummy()):
            s += 10000
        return s

    compiled = main.compile_function()
    validate(compiled)

    # Check we have main, and 2 monomorphizations of foo (Dummy constructor is inlined)
    assert len(funcs_defs(compiled.modules[0])) == 3

    run_int_fn(main, 101)


@pytest.mark.xfail(reason="https://github.com/quantinuum/guppylang/issues/1030")
def test_int(validate):
    IT = guppy.const_var("IT", "int§")

    @guppy.struct
    class Dummy(Generic[IT]):
        """Unit struct type to introduce generic I into the signature of `foo` below.

        This is needed because we don't support the `def foo[I: int]` syntax yet to
        introduce type params that are not referenced in the signature.
        """

    @guppy
    def foo(_: Dummy[IT]) -> float:
        return IT

    @guppy
    def main() -> float:
        return (
            foo[1](Dummy())
            + foo[2](Dummy())
            + foo[-2](Dummy())
            + foo[3](Dummy())
            + foo[1](Dummy())
            + foo[1](Dummy())
        )

    compiled = main.compile_function()
    validate(compiled)

    # Check we have main, and 4 monomorphizations of foo (Dummy constructor is inlined)
    assert len(funcs_defs(compiled.modules[0])) == 5


def test_float(validate, run_float_fn_approx):
    F = guppy.const_var("F", "float")

    @guppy.struct
    class Dummy(Generic[F]):
        """Unit struct type to introduce generic F into the signature of `foo` below.

        This is needed because we don't support the `def foo[F: float]` syntax yet to
        introduce type params that are not referenced in the signature.
        """

    @guppy
    def foo(_: Dummy[F]) -> float:
        return F

    @guppy
    def main() -> float:
        return (
            foo[1.5](Dummy())
            + foo[2.5](Dummy())
            + foo[3.5](Dummy())
            + foo[1.5](Dummy())
            + foo[1.5](Dummy())
        )

    compiled = main.compile_function()
    validate(compiled)

    # Check we have main, and 3 monomorphizations of foo (Dummy constructor is inlined)
    assert len(funcs_defs(compiled.modules[0])) == 4

    run_float_fn_approx(main, 10.5)


@pytest.mark.xfail(reason="https://github.com/quantinuum/guppylang/issues/1030")
def test_string(validate):
    S = guppy.const_var("S", "str")

    @guppy.struct
    class Dummy(Generic[S]):
        """Unit struct type to introduce generic S into the signature of `foo` below.

        This is needed because we don't support the `def foo[S: str]` syntax yet to
        introduce type params that are not referenced in the signature.
        """

    @guppy
    def foo(_: Dummy[S]) -> str:
        return S

    @guppy
    def main() -> tuple[str, str, str, str, str]:
        return (
            foo[""](Dummy()),
            foo["a"](Dummy()),
            foo["A"](Dummy()),
            foo["ä"](Dummy()),
            foo["a"](Dummy()),
        )

    compiled = main.compile_function()
    validate(compiled)

    # Check we have main, and 4 monomorphizations of foo (Dummy constructor is inlined)
    assert len(funcs_defs(compiled.modules[0])) == 5


def test_chain(validate, run_int_fn):
    B = guppy.const_var("B", "bool")

    @guppy.struct
    class Dummy(Generic[B]):
        """Unit struct type to introduce generic B into the signatures below.

        This is needed because we don't support the `def foo[B: bool]` syntax yet to
        introduce type params that are not referenced in the signature.
        """

    @guppy
    def a(x: Dummy[B]) -> bool:
        return b(x)

    @guppy
    def b(x: Dummy[B]) -> bool:
        return c(x)

    @guppy
    def c(x: Dummy[B]) -> bool:
        return d(x)

    @guppy
    def d(_: Dummy[B]) -> bool:
        return B

    @guppy
    def main() -> int:
        x = a[True](Dummy())
        b[True](Dummy())
        c[True](Dummy())
        d[True](Dummy())
        return 1 if x else 0

    compiled = main.compile_function()
    validate(compiled)

    # Check we have main, and 4 monomorphizations (a, b, c, d)
    assert len(funcs_defs(compiled.modules[0])) == 5

    run_int_fn(main, 1)


def test_recursion(validate):
    B = guppy.const_var("B", "bool")

    @guppy.struct
    class Dummy(Generic[B]):
        """Unit struct type to introduce generic B into the signatures below.

        This is needed because we don't support the `def foo[B: bool]` syntax yet to
        introduce type params that are not referenced in the signature.
        """

    @guppy
    def foo(_: Dummy[B]) -> int:
        return bar[True](Dummy()) + foo[False](Dummy())

    @guppy
    def bar(_: Dummy[B]) -> int:
        return foo[True](Dummy()) + bar[False](Dummy())

    @guppy
    def baz(d: Dummy[B]) -> int:
        return foo(d)

    @guppy
    def main() -> int:
        return baz[True](Dummy())

    compiled = main.compile_function()
    validate(compiled)

    # Check we have main, and 5 monomorphizations of foo/bar/baz
    assert len(funcs_defs(compiled.modules[0])) == 6


def test_many(validate):
    B = guppy.const_var("B", "bool")
    F = guppy.const_var("F", "float")
    N = guppy.nat_var("N")

    T1 = guppy.type_var("T1")
    T2 = guppy.type_var("T2")
    T3 = guppy.type_var("T3")

    @guppy.struct
    class MyStruct(Generic[T1, B, T2, N, T3, F]):
        """Unit struct type to introduce generics into the signatures below.

        This is needed because we don't support the `def foo[S: str]` syntax yet to
        introduce type params that are not referenced in the signature.
        """

        x1: T1
        x2: T2
        x3s: array[T3, N]

    @guppy.declare
    def bar(xs: array[T1, N]) -> None: ...

    @guppy
    def baz(s: MyStruct[T1, B, T2, N, T3, F]) -> MyStruct[T1, B, T2, N, T3, F]:
        return baz(s)

    @guppy
    def foo(s: MyStruct[int, False, T2, N, T3, F]) -> float:
        bar(s.x3s)
        baz(s)
        return N + F

    @guppy
    def main() -> None:
        s1: MyStruct[int, False, float, 3, bool, 4.2] = MyStruct(
            1, 1.0, array(True, False, True)
        )
        s1 = baz(baz(s1))
        bar(s1.x3s)
        foo(s1)

        s2: MyStruct[int, False, bool, 1, nat, 4.2] = MyStruct(0, False, array(nat(42)))
        s2 = baz(baz(s2))
        bar(s2.x3s)
        foo(s2)

        s3: MyStruct[int, False, bool, 1, float, 1.5] = MyStruct(0, False, array(4.2))
        s3 = baz(baz(s3))
        bar(s3.x3s)
        foo(s3)

    compiled = main.compile_function()
    validate(compiled)

    # Check we have main, and 2 monomorphizations of foo and baz each. Note that `s2`
    # doesn't generate a monomorphisation since it shares the relevant mono-parameters
    # with `s1`
    assert len(funcs_defs(compiled.modules[0])) == 5


def test_constructor(validate):
    B = guppy.const_var("B", "bool")
    F = guppy.const_var("F", "float")

    @guppy.struct
    class MyStruct(Generic[B, F]):
        pass

    @guppy
    def main() -> None:
        s1: MyStruct[True, 1.0] = MyStruct()  # This is inlined
        s2: MyStruct[False, 1.0] = MyStruct()  # This is inlined
        f1 = MyStruct[True, 2.0]  # This is monomorphized
        f2 = MyStruct[False, 2.0]  # This is monomorphized
        f1()
        f2()

    compiled = main.compile_function()
    validate(compiled)

    # Check we have main, and 2 monomorphizations of the MyStruct constructor
    assert len(funcs_defs(compiled.modules[0])) == 3


def test_higher_order(validate):
    B = guppy.const_var("B", "bool")
    F = guppy.const_var("F", "float")

    @guppy.struct
    class Struct(Generic[B, F]):
        pass

    @guppy
    def fun1(x: Struct[B, F]) -> None:
        pass

    @guppy
    def fun2(x: Struct[True, F]) -> None:
        pass

    @guppy
    def fun3(x: Struct[B, 42.0]) -> None:
        pass

    @guppy
    def foo(f: Callable[[Struct[B, 42.0]], None]) -> None:
        pass

    @guppy
    def main() -> None:
        foo[True](fun1)
        foo[False](fun1)
        foo(fun2)
        foo(fun3[False])
        foo(fun3[True])

    compiled = main.compile_function()
    validate(compiled)

    # Check we have main, fun2, and 2 monomorphizations of fun1, fun3, and foo each
    assert len(funcs_defs(compiled.modules[0])) == 8


def test_nat_generic(validate):
    T = guppy.type_var("T", copyable=True, droppable=True)

    @guppy
    def foo(t: T @ comptime) -> T:
        return t

    @guppy
    def main(n: nat @ comptime, m: nat @ comptime) -> None:
        foo(n)
        foo(m)
        foo(True)
        foo(False)

    compiled = main.compile()
    validate(compiled)

    # Check we have main, and 3 monomorphisations of foo. The two nat versions should
    # correspond to the same monomorphisation since the bounded nat args are preserved
    # in Hugr!
    assert len(funcs_defs(compiled.modules[0])) == 4
