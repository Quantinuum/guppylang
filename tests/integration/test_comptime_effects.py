"""Tests of effects annotation for comptime callers/callees."""

import pytest

from guppylang.decorator import Effect, guppy
from guppylang.std.builtins import result
from guppylang.std.effects import ANY


def test_pure_from_impure_comptime(validate):
    @guppy(effects=None)
    def pure_func(x: int) -> int:
        return x + 1

    @guppy.comptime
    def normal_func(x: int) -> int:
        return pure_func(x) + 2

    validate(normal_func.compile_function())


def test_pure_comptime_from_impure(validate):
    @guppy.comptime(effects=None)
    def pure_func(x: int) -> int:
        return x + 1

    @guppy
    def normal_func(x: int) -> int:
        return pure_func(x) + 2

    validate(normal_func.compile_function())


def test_comptime_pure_from_impure(validate):
    @guppy.comptime(effects=[])
    def pure_func(x: int) -> int:
        return x + 1

    @guppy.comptime
    def normal_func(x: int) -> int:
        return pure_func(x) + 2

    validate(normal_func.compile_function())


def test_pure_from_explicit_comptime_impure(validate):
    @guppy(effects=[])
    def pure_func(x: int) -> int:
        return x + 1

    @guppy.comptime(effects=ANY)
    def normal_func(x: int) -> int:
        return pure_func(x) + 2

    validate(normal_func.compile_function())


def test_pure_comptime_from_explicit_impure(validate):
    @guppy.comptime(effects=None)
    def pure_func(x: int) -> int:
        return x + 1

    @guppy(effects=[Effect.ANY])
    def normal_func(x: int) -> int:
        return pure_func(x) + 2

    validate(normal_func.compile_function())


def test_comptime_pure_from_explicit_impure(validate):
    @guppy.comptime(effects=[])
    def pure_func(x: int) -> int:
        return x + 1

    @guppy.comptime
    def normal_func(x: int) -> int:
        return pure_func(x) + 2

    validate(normal_func.compile_function())


@pytest.mark.parametrize(
    ("caller_flags", "callee"),
    [
        ({"effects": [Effect.ANY]}, {}),
        ({}, {"effects": [Effect.ANY]}),
        ({"effects": [Effect.ANY]}, {"effects": [Effect.ANY]}),
    ],
)
def test_impure_explicit_from_comptime(caller_flags, callee, validate):
    @guppy(**callee)
    def impure_func(x: int) -> int:
        result("tag", x)
        return x + 3

    @guppy.comptime(**caller_flags)
    def caller(x: int) -> int:
        return impure_func(x) + 1

    validate(caller.compile_function())


@pytest.mark.parametrize(
    ("caller", "callee"),
    [
        ({"effects": [Effect.ANY]}, {}),
        ({}, {"effects": [Effect.ANY]}),
        ({"effects": [Effect.ANY]}, {"effects": [Effect.ANY]}),
    ],
)
@pytest.mark.parametrize(
    ("caller_deco", "callee_deco"),
    [
        (guppy.comptime, guppy),
        (guppy, guppy.comptime),
        (guppy.comptime, guppy.comptime),
    ],
)
def test_impure_explicit_comptime_callee(
    caller, callee, caller_deco, callee_deco, validate
):
    @callee_deco(**callee)
    def impure_func(x: int) -> int:
        result("tag", x)
        return x + 3

    @caller_deco(**caller)
    def impure_func2(x: int) -> int:
        return impure_func(x) + 1

    validate(impure_func2.compile_function())


def test_pure_from_pure_comptime(validate):
    @guppy(effects=[])
    def pure_func1(x: int) -> int:
        return x + 1

    @guppy.comptime(effects=None)
    def pure_func2(x: int) -> int:
        return pure_func1(pure_func1(x)) + 1

    validate(pure_func2.compile_function())


def test_pure_comptime_from_pure(validate):
    @guppy.comptime(effects=None)
    def pure_func1(x: int) -> int:
        return x + 1

    @guppy(effects=[])
    def pure_func2(x: int) -> int:
        return pure_func1(pure_func1(x)) + 1

    validate(pure_func2.compile_function())


def test_comptime_pure_from_pure(validate):
    @guppy.comptime(effects=[])
    def pure_func1(x: int) -> int:
        return x + 1

    @guppy.comptime(effects=[])
    def pure_func2(x: int) -> int:
        return pure_func1(pure_func1(x)) + 1

    validate(pure_func2.compile_function())
