"""Tests of effects annotation."""

import pytest
from collections.abc import Callable

from guppylang.decorator import guppy, Effect
from guppylang.std.builtins import result
from guppylang.std.effects import effects, ANY


def test_pure_decl_from_impure(validate):
    @guppy.declare(effects=[])
    def pure_func(x: int) -> int: ...

    @guppy
    def impure_func(x: int) -> int:
        return pure_func(x) + 1

    validate(impure_func.compile_function())


def test_pure_decl_from_explicit_impure(validate):
    @guppy.declare(effects=[])
    def pure_func(x: int) -> int: ...

    @guppy(effects=[Effect.ANY])
    def impure_func(x: int) -> int:
        return pure_func(x) + 1

    validate(impure_func.compile_function())


def test_pure_decl_from_pure(validate):
    @guppy.declare(effects=[])
    def pure_func1(x: int) -> int: ...

    @guppy(effects=[])
    def pure_func2(x: int) -> int:
        return pure_func1(x) + 2

    validate(pure_func2.compile_function())


@pytest.mark.parametrize(
    ("caller", "callee"),
    [
        ({"effects": [Effect.ANY]}, {}),
        ({}, {"effects": [Effect.ANY]}),
        ({"effects": [Effect.ANY]}, {"effects": [Effect.ANY]}),
    ],
)
def test_impure_decl_explicit(caller, callee, validate):
    @guppy.declare(**callee)
    def impure_func(x: int) -> int: ...

    @guppy(**caller)
    def impure_func2(x: int) -> int:
        return impure_func(x) + 1

    validate(impure_func2.compile_function())


def test_pure_from_impure(validate):
    @guppy(effects=[])
    def pure_func(x: int) -> int:
        return x + 1

    @guppy
    def normal_func(x: int) -> int:
        return pure_func(x) + 2

    validate(normal_func.compile_function())


def test_pure_from_explicit_impure(validate):
    @guppy(effects=[])
    def pure_func(x: int) -> int:
        return x + 1

    @guppy(effects=[Effect.ANY])
    def normal_func(x: int) -> int:
        return pure_func(x) + 2

    validate(normal_func.compile_function())


@pytest.mark.parametrize(
    ("caller", "callee"),
    [
        ({"effects": [Effect.ANY]}, {}),
        ({}, {"effects": [Effect.ANY]}),
        ({"effects": [Effect.ANY]}, {"effects": [Effect.ANY]}),
    ],
)
def test_impure_explicit(caller, callee, validate):
    @guppy(**callee)
    def impure_func(x: int) -> int:
        result("tag", x)
        return x + 3

    @guppy(**caller)
    def impure_func2(x: int) -> int:
        return impure_func(x) + 1

    validate(impure_func2.compile_function())


def test_pure_from_pure(validate):
    @guppy(effects=[])
    def pure_func1(x: int) -> int:
        return x + 1

    @guppy(effects=[])
    def pure_func2(x: int) -> int:
        return pure_func1(pure_func1(x)) + 1

    validate(pure_func2.compile_function())


def test_pure_callable_from_impure(validate):
    @guppy
    def impure_func(pure_f: Callable[[int], int] @ effects()) -> int:
        return pure_f(5) + 1

    validate(impure_func.compile_function())


def test_pure_callable_from_pure(validate):
    @guppy(effects=[])
    def pure_func(pure_f: Callable[[int], int] @ effects()) -> int:
        return pure_f(5) + 1

    validate(pure_func.compile_function())


def test_pure_callable_from_impure_explicit(validate):
    @guppy(effects=[Effect.ANY])
    def impure_func(pure_f: Callable[[int], int] @ effects()) -> int:
        return pure_f(5) + 1

    validate(impure_func.compile_function())


def test_return_callable1(validate):
    @guppy
    def impure_func(x: int) -> int:
        return x + 1

    @guppy(effects=[])
    def higher_order() -> Callable[[int], int] @ effects(ANY):
        return impure_func

    validate(higher_order.compile_function())


def test_return_callable2(validate):
    @guppy(effects=[Effect.ANY])
    def explicit_impure_func(x: int) -> int:
        return x + 1

    @guppy(effects=[])
    def higher_order() -> Callable[[int], int]:
        return explicit_impure_func

    validate(higher_order.compile_function())
