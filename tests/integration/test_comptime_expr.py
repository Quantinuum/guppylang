"""Tests for using python expressions in guppy functions."""

from guppylang.decorator import guppy
from guppylang.std.builtins import py, comptime, array, frozenarray, nat, owned
from tests.util import compile_guppy


def test_basic(validate):
    x = 42

    @guppy
    def foo() -> int:
        return comptime(x + 1)

    validate(foo.compile_function())


def test_py_alias(validate):
    x = 42

    @guppy
    def foo() -> int:
        return py(x + 1)

    validate(foo.compile_function())


def test_builtin(validate):
    @compile_guppy
    def foo() -> int:
        return comptime(len({"a": 1337, "b": None}))

    validate(foo)


def test_if(validate):
    b = True

    @guppy
    def foo() -> int:
        if comptime(b or 1 > 6):
            return 0
        return 1

    validate(foo.compile_function())


def test_redeclare_after(validate):
    x = 1

    @guppy
    def foo() -> bool:
        return comptime(x)

    x = False

    validate(foo.compile_function())


def test_tuple(validate):
    @compile_guppy
    def foo() -> int:
        x, _y = comptime((1, False))
        return x

    validate(foo)


def test_tuple_implicit(validate):
    @compile_guppy
    def foo() -> int:
        x, _y = comptime(1, False)
        return x

    validate(foo)


def test_list_basic(validate):
    @compile_guppy
    def foo() -> frozenarray[int, 3]:
        xs = comptime([1, 2, 3])
        return xs

    validate(foo)


def test_list_empty(validate):
    @compile_guppy
    def foo() -> frozenarray[int, 0]:
        return comptime([])

    validate(foo)


def test_list_empty_nested(validate):
    @compile_guppy
    def foo() -> None:
        xs: frozenarray[tuple[int, frozenarray[bool, 0]], 1] = comptime([(42, [])])

    validate(foo)


def test_list_empty_multiple(validate):
    @compile_guppy
    def foo() -> None:
        xs: tuple[frozenarray[int, 0], frozenarray[bool, 0]] = comptime([], [])

    validate(foo)


def test_nats_from_ints(validate):
    @compile_guppy
    def foo() -> None:
        x: nat = comptime(1)
        y: tuple[nat, nat] = comptime(2, 3)
        z: frozenarray[nat, 3] = comptime([4, 5, 6])

    validate(foo)


def test_strings(validate):
    @compile_guppy
    def foo() -> None:
        x: str = comptime("a" + "b")

    validate(foo)


def test_comprehension(validate):
    """See https://github.com/quantinuum/guppylang/issues/1207"""
    py_lst = [x for x in range(10)]

    @guppy
    def main() -> None:
        comptime([py_lst[i] for i in range(len(py_lst))])

    main.check()


def test_func_type_arg(validate):
    n = 10

    @guppy
    def foo(xs: array[int, comptime(n)] @ owned) -> array[int, comptime(n)]:
        return xs

    @guppy.declare
    def bar(xs: array[int, comptime(n)]) -> array[int, comptime(n)]: ...

    @guppy.struct
    class Baz:
        xs: array[int, comptime(n)]

    validate(foo.compile_function())
    validate(bar.compile_function())
    validate(Baz.compile())


def test_subscript_assign(validate):
    n = 5

    @guppy
    def subscript(xs: array[int, 10]) -> None:
        xs[comptime(n)] = 0

    validate(subscript.compile_function())


def test_subscript_augmenting_assign(validate):
    n = 5

    @guppy
    def subscript(xs: array[int, 10]) -> None:
        xs[comptime(n)] += 0

    validate(subscript.compile_function())


def test_subscript_annotated_assign(validate):
    n = 5

    @guppy
    def subscript(xs: array[int, 10]) -> None:
        xs[comptime(n)]: int = 0

    validate(subscript.compile_function())
