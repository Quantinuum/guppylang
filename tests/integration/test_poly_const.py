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
    def foo_struct(_: Dummy[B]) -> bool:
        return B

    @guppy
    def main_struct() -> int:
        s = 0
        if foo_struct[True](Dummy()):
            s += 1
        if foo_struct[False](Dummy()):
            s += 10
        if foo_struct[True](Dummy()):
            s += 100
        if foo_struct[False](Dummy()):
            s += 10000
        return s

    compiled_struct = main_struct.compile_function()
    validate(compiled_struct)

    # Check we have main_struct, and 2 monomorphizations of foo_struct
    # (Dummy constructor is inlined)
    assert len(funcs_defs(compiled_struct.modules[0])) == 3

    run_int_fn(main_struct, 101)

    @guppy.enum
    class DummyEnum(Generic[B]):  # pyright: ignore[reportInvalidTypeForm]
        VariantA = {}  # noqa: RUF012

    @guppy
    def foo_enum(_: DummyEnum[B]) -> bool:
        return B

    @guppy
    def main_enum() -> int:
        s = 0
        if foo_enum[True](DummyEnum.VariantA[True]()):
            s += 1
        if foo_enum[False](DummyEnum.VariantA[False]()):
            s += 10
        if foo_enum[True](DummyEnum.VariantA[True]()):
            s += 100
        if foo_enum[False](DummyEnum.VariantA[False]()):
            s += 10000
        return s

    compiled_enum = main_enum.compile_function()
    validate(compiled_enum)

    # Check we have main_enum, and 2 monomorphizations of foo_enum, 2 for VariantA()
    assert len(funcs_defs(compiled_enum.modules[0])) == 5

    run_int_fn(main_enum, 101)


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
    def foo_struct(_: Dummy[IT]) -> float:
        return IT

    @guppy
    def main_struct() -> float:
        return (
            foo_struct[1](Dummy())
            + foo_struct[2](Dummy())
            + foo_struct[-2](Dummy())
            + foo_struct[3](Dummy())
            + foo_struct[1](Dummy())
            + foo_struct[1](Dummy())
        )

    compiled_struct = main_struct.compile_function()
    validate(compiled_struct)

    # Check we have main_struct, and 4 monomorphizations of foo_struct
    # (Dummy constructor is inlined)
    assert len(funcs_defs(compiled_struct.modules[0])) == 5

    @guppy.enum
    class DummyEnum(Generic[IT]):  # pyright: ignore[reportInvalidTypeForm]
        VariantA = {}  # noqa: RUF012

    @guppy
    def foo_enum(_: DummyEnum[IT]) -> float:
        return IT

    @guppy
    def main_enum() -> float:
        return (
            foo_enum[1](DummyEnum.VariantA())
            + foo_enum[2](DummyEnum.VariantA())
            + foo_enum[-3](DummyEnum.VariantA())
            + foo_enum[1](DummyEnum.VariantA())
            + foo_enum[1](DummyEnum.VariantA())
        )

    compiled_enum = main_enum.compile_function()
    validate(compiled_enum)

    # Check we have main_enum, and 3 monomorphizations of foo_enum, 3 for VariantA()
    assert len(funcs_defs(compiled_enum.modules[0])) == 7


def test_float(validate, run_float_fn_approx):
    F = guppy.const_var("F", "float")

    @guppy.struct
    class Dummy(Generic[F]):
        """Unit struct type to introduce generic F into the signature of `foo` below.

        This is needed because we don't support the `def foo[F: float]` syntax yet to
        introduce type params that are not referenced in the signature.
        """

    @guppy
    def foo_struct(_: Dummy[F]) -> float:
        return F

    @guppy
    def main_struct() -> float:
        return (
            foo_struct[1.5](Dummy())
            + foo_struct[2.5](Dummy())
            + foo_struct[3.5](Dummy())
            + foo_struct[1.5](Dummy())
            + foo_struct[1.5](Dummy())
        )

    compiled_struct = main_struct.compile_function()
    validate(compiled_struct)

    # Check we have main_struct, and 3 monomorphizations of foo_struct
    # (Dummy constructor is inlined)
    assert len(funcs_defs(compiled_struct.modules[0])) == 4

    run_float_fn_approx(main_struct, 10.5)

    @guppy.enum
    class DummyEnum(Generic[F]):  # pyright: ignore[reportInvalidTypeForm]
        VariantA = {}  # noqa: RUF012

    @guppy
    def foo_enum(_: DummyEnum[F]) -> float:
        return F

    @guppy
    def main_enum() -> float:
        return (
            foo_enum[1.5](DummyEnum.VariantA())
            + foo_enum[2.5](DummyEnum.VariantA())
            + foo_enum[3.5](DummyEnum.VariantA())
            + foo_enum[1.5](DummyEnum.VariantA())
            + foo_enum[1.5](DummyEnum.VariantA())
        )

    compiled_enum = main_enum.compile_function()
    validate(compiled_enum)

    # Check we have main_enum, and 3 monomorphizations of foo_enum
    assert len(funcs_defs(compiled_enum.modules[0])) == 4

    run_float_fn_approx(main_enum, 10.5)


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
    def foo_struct(_: Dummy[S]) -> str:
        return S

    @guppy
    def main_struct() -> tuple[str, str, str, str, str]:
        return (
            foo_struct[""](Dummy()),
            foo_struct["a"](Dummy()),
            foo_struct["A"](Dummy()),
            foo_struct["ä"](Dummy()),
            foo_struct["a"](Dummy()),
        )

    compiled_struct = main_struct.compile_function()
    validate(compiled_struct)

    # Check we have main_struct, and 4 monomorphizations of foo_struct
    # (Dummy constructor is inlined)
    assert len(funcs_defs(compiled_struct.modules[0])) == 5


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
    def main_struct() -> int:
        x = a[True](Dummy())
        b[True](Dummy())
        c[True](Dummy())
        d[True](Dummy())
        return 1 if x else 0

    compiled_struct = main_struct.compile_function()
    validate(compiled_struct)

    # Check we have main_struct, and 4 monomorphizations (a, b, c, d)
    assert len(funcs_defs(compiled_struct.modules[0])) == 5

    run_int_fn(main_struct, 1)

    @guppy.enum
    class DummyEnum(Generic[B]):  # pyright: ignore[reportInvalidTypeForm]
        VariantA = {}  # noqa: RUF012

    @guppy
    def a_enum(x: DummyEnum[B]) -> bool:
        return b_enum(x)

    @guppy
    def b_enum(x: DummyEnum[B]) -> bool:
        return c_enum(x)

    @guppy
    def c_enum(x: DummyEnum[B]) -> bool:
        return d_enum(x)

    @guppy
    def d_enum(_: DummyEnum[B]) -> bool:
        return B

    @guppy
    def main_enum() -> int:
        x = a_enum[True](DummyEnum.VariantA[True]())
        b_enum[True](DummyEnum.VariantA[True]())
        c_enum[True](DummyEnum.VariantA[True]())
        d_enum[True](DummyEnum.VariantA[True]())
        return 1 if x else 0

    compiled_enum = main_enum.compile_function()
    validate(compiled_enum)

    # Check we have main_enum, 4 monomorphizations (a_enum, b_enum, c_enum, d_enum) and
    # VariantA() monomorphized for True
    assert len(funcs_defs(compiled_enum.modules[0])) == 6

    run_int_fn(main_enum, 1)


def test_recursion(validate):
    B = guppy.const_var("B", "bool")

    @guppy.struct
    class Dummy(Generic[B]):
        """Unit struct type to introduce generic B into the signatures below.

        This is needed because we don't support the `def foo[B: bool]` syntax yet to
        introduce type params that are not referenced in the signature.
        """

    @guppy
    def foo_struct(_: Dummy[B]) -> int:
        return bar[True](Dummy()) + foo_struct[False](Dummy())

    @guppy
    def bar(_: Dummy[B]) -> int:
        return foo_struct[True](Dummy()) + bar[False](Dummy())

    @guppy
    def baz(d: Dummy[B]) -> int:
        return foo_struct(d)

    @guppy
    def main_struct() -> int:
        return baz[True](Dummy())

    compiled_struct = main_struct.compile_function()
    validate(compiled_struct)

    # Check we have main_struct, and 5 monomorphizations of foo_struct/bar/baz
    assert len(funcs_defs(compiled_struct.modules[0])) == 6

    @guppy.enum
    class DummyEnum(Generic[B]):  # pyright: ignore[reportInvalidTypeForm]
        VariantA = {}  # noqa: RUF012

    @guppy
    def foo_enum(_: DummyEnum[B]) -> int:
        return bar_enum[True](DummyEnum.VariantA[True]()) + foo_enum[False](
            DummyEnum.VariantA[False]()
        )

    @guppy
    def bar_enum(_: DummyEnum[B]) -> int:
        return foo_enum[True](DummyEnum.VariantA[True]()) + bar_enum[False](
            DummyEnum.VariantA[False]()
        )

    @guppy
    def baz_enum(d: DummyEnum[B]) -> int:
        return foo_enum(d)

    @guppy
    def main_enum() -> int:
        return baz_enum[True](DummyEnum.VariantA[True]())

    compiled_enum = main_enum.compile_function()
    validate(compiled_enum)

    # Check we have main_enum, and 5 monomorphizations of foo_enum/bar_enum/baz_enum
    # plus 2 for VariantA() (one for True and one for False)
    assert len(funcs_defs(compiled_enum.modules[0])) == 8


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
    def foo_struct(s: MyStruct[int, False, T2, N, T3, F]) -> float:
        bar(s.x3s)
        baz(s)
        return N + F

    @guppy
    def main_struct() -> None:
        s1: MyStruct[int, False, float, 3, bool, 4.2] = MyStruct(
            1, 1.0, array(True, False, True)
        )
        s1 = baz(baz(s1))
        bar(s1.x3s)
        foo_struct(s1)

        s2: MyStruct[int, False, bool, 1, nat, 4.2] = MyStruct(0, False, array(nat(42)))
        s2 = baz(baz(s2))
        bar(s2.x3s)
        foo_struct(s2)

        s3: MyStruct[int, False, bool, 1, float, 1.5] = MyStruct(0, False, array(4.2))
        s3 = baz(baz(s3))
        bar(s3.x3s)
        foo_struct(s3)

    compiled_struct = main_struct.compile_function()
    validate(compiled_struct)

    # Check we have main_struct, and 3 monomorphizations of foo and baz each
    assert len(funcs_defs(compiled_struct.modules[0])) == 7

    # Enum equivalent: same const-generic parameters, but no field access (enums are
    # opaque until pattern-matched), so the enum is passed through baz_enum/foo_enum
    @guppy.enum
    class MyEnum(Generic[T1, B, T2, N, T3, F]):  # pyright: ignore[reportInvalidTypeForm]
        VariantA = {}  # noqa: RUF012

    @guppy
    def baz_enum(
        e: MyEnum[T1, B, T2, N, T3, F],
    ) -> MyEnum[T1, B, T2, N, T3, F]:
        return baz_enum(e)

    @guppy
    def foo_enum(e: MyEnum[int, False, T2, N, T3, F]) -> float:
        baz_enum(e)
        return N + F

    @guppy
    def main_enum() -> None:
        e1: MyEnum[int, False, float, 3, bool, 4.2] = MyEnum.VariantA[
            int, False, float, 3, bool, 4.2
        ]()
        e1 = baz_enum(baz_enum(e1))
        foo_enum(e1)

        e2: MyEnum[int, False, bool, 1, nat, 4.2] = MyEnum.VariantA[
            int, False, bool, 1, nat, 4.2
        ]()
        e2 = baz_enum(baz_enum(e2))
        foo_enum(e2)

        e3: MyEnum[int, False, bool, 1, float, 1.5] = MyEnum.VariantA[
            int, False, bool, 1, float, 1.5
        ]()
        e3 = baz_enum(baz_enum(e3))
        foo_enum(e3)

    compiled_enum = main_enum.compile_function()
    validate(compiled_enum)

    # Check we have main_enum, 3 monomorphizations of foo_enum and baz_enum each,
    # 3 for VariantA() (float, nat, bool)
    assert len(funcs_defs(compiled_enum.modules[0])) == 10


def test_constructor(validate):
    B = guppy.const_var("B", "bool")
    F = guppy.const_var("F", "float")

    @guppy.struct
    class MyStruct(Generic[B, F]):
        pass

    @guppy
    def main_struct() -> None:
        s1: MyStruct[True, 1.0] = MyStruct()  # This is inlined
        s2: MyStruct[False, 1.0] = MyStruct()  # This is inlined
        f1 = MyStruct[True, 2.0]  # This is monomorphized
        f2 = MyStruct[False, 2.0]  # This is monomorphized
        f1()
        f2()

    compiled_struct = main_struct.compile_function()
    validate(compiled_struct)

    # Check we have main_struct, and 2 monomorphizations of the MyStruct constructor
    assert len(funcs_defs(compiled_struct.modules[0])) == 3

    @guppy.enum
    class MyEnum(Generic[B, F]):  # pyright: ignore[reportInvalidTypeForm]
        VariantA = {}  # noqa: RUF012

    @guppy
    def main_enum() -> None:
        e1: MyEnum[True, 1.0] = MyEnum.VariantA[True, 1.0]()  # This is inlined
        e2: MyEnum[False, 1.0] = MyEnum.VariantA[False, 1.0]()  # This is inlined
        f1 = MyEnum.VariantA[True, 2.0]  # This is monomorphized
        f2 = MyEnum.VariantA[False, 2.0]  # This is monomorphized
        f1()
        f2()

    compiled_enum = main_enum.compile_function()
    validate(compiled_enum)

    # Check we have main_enum, and 4 monomorphizations of the MyEnum.VariantA
    assert len(funcs_defs(compiled_enum.modules[0])) == 5


def test_higher_order(validate):
    B = guppy.const_var("B", "bool")
    F = guppy.const_var("F", "float")

    @guppy.struct
    class Struct(Generic[B, F]):
        pass

    @guppy
    def sfun1(x: Struct[B, F]) -> None:
        pass

    @guppy
    def sfun2(x: Struct[True, F]) -> None:
        pass

    @guppy
    def sfun3(x: Struct[B, 42.0]) -> None:
        pass

    @guppy
    def sfoo(f: Callable[[Struct[B, 42.0]], None]) -> None:
        pass

    @guppy
    def main_struct() -> None:
        sfoo[True](sfun1)
        sfoo[False](sfun1)
        sfoo(sfun2)
        sfoo(sfun3[False])
        sfoo(sfun3[True])

    compiled_struct = main_struct.compile_function()
    validate(compiled_struct)

    # Check we have main_struct, fun2, and 2 monomorphizations of fun1, fun3,
    # and sfoo each
    assert len(funcs_defs(compiled_struct.modules[0])) == 8

    @guppy.enum
    class EnumType(Generic[B, F]):  # pyright: ignore[reportInvalidTypeForm]
        VariantA = {}  # noqa: RUF012

    @guppy
    def efun1(x: EnumType[B, F]) -> None:
        pass

    @guppy
    def efun2(x: EnumType[True, F]) -> None:
        pass

    @guppy
    def efun3(x: EnumType[B, 42.0]) -> None:
        pass

    @guppy
    def efoo(f: Callable[[EnumType[B, 42.0]], None]) -> None:
        pass

    @guppy
    def main_enum() -> None:
        efoo[True](efun1)
        efoo[False](efun1)
        efoo(efun2)
        efoo(efun3[False])
        efoo(efun3[True])

    compiled_enum = main_enum.compile_function()
    validate(compiled_enum)

    # Check we have main_enum, efun2, and 2 monomorphizations of efun1,
    # efun3, and efoo each
    assert len(funcs_defs(compiled_enum.modules[0])) == 8


def test_nat_generic(validate):
    T = guppy.type_var("T", copyable=True, droppable=True)

    @guppy
    def foo(t: T @ comptime) -> T:
        return t

    @guppy
    def bar(n: nat @ comptime, m: nat @ comptime) -> None:
        foo(n)
        foo(m)
        foo(True)
        foo(False)

    @guppy
    def main() -> None:
        bar(1, 2)

    compiled = main.compile()
    validate(compiled)

    # Check we have main, bar, and 4 monomorphisations of foo
    assert len(funcs_defs(compiled.modules[0])) == 6
