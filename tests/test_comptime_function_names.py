"""Comptime functions use the same qualified names as checked Guppy functions."""

from guppylang import guppy
from hugr.ops import FuncDefn


def function_names(package):
    hugr = package.modules[0]
    return [
        hugr[n].op.f_name
        for n in hugr.children(hugr.module_root)
        if isinstance(hugr[n].op, FuncDefn)
    ]


def test_comptime_qualified_name():
    @guppy.comptime
    def function() -> None:
        pass

    names = function_names(function.with_minimal_opt().compile())
    assert f"{__name__}.test_comptime_qualified_name.<locals>.function" in names


def test_comptime_generic_names_are_distinct():
    @guppy.comptime
    def identity[T](value: T) -> T:
        return value

    @guppy
    def main() -> None:
        _ = identity(1)
        _ = identity(True)

    names = function_names(main.with_minimal_opt().compile())
    prefix = f"{__name__}.test_comptime_generic_names_are_distinct.<locals>.identity"
    assert f"{prefix}$int" in names
    assert f"{prefix}$bool" in names


def test_comptime_constant_names():
    from guppylang.std.array import array

    n = guppy.nat_var("n")

    @guppy.comptime
    def values() -> array[int, n]:
        return list(range(n))

    @guppy
    def main() -> None:
        _ = values[2]()
        _ = values[3]()

    names = function_names(main.with_minimal_opt().compile())
    prefix = f"{__name__}.test_comptime_constant_names.<locals>.values"
    assert f"{prefix}$2" in names
    assert f"{prefix}$3" in names


def test_comptime_same_name_different_scopes():
    def first_scope():
        @guppy.comptime
        def same_name() -> int:
            return 1

        return same_name

    def second_scope():
        @guppy.comptime
        def same_name() -> int:
            return 2

        return same_name

    first = first_scope()
    second = second_scope()

    @guppy
    def main() -> int:
        return first() + second()

    names = function_names(main.with_minimal_opt().compile())
    prefix = f"{__name__}.test_comptime_same_name_different_scopes.<locals>"
    assert f"{prefix}.first_scope.<locals>.same_name" in names
    assert f"{prefix}.second_scope.<locals>.same_name" in names
