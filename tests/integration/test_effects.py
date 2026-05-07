"""Tests of max_effects annotation."""

from guppylang.decorator import guppy


def test_pure_decl_from_impure(validate):
    @guppy.declare(max_effects=[])
    def pure_func(x: int) -> int: ...

    @guppy
    def impure_func(x: int) -> int:
        return pure_func(x) + 1

    validate(impure_func.compile_function())


def test_pure_decl_from_pure(validate):
    @guppy.declare(max_effects=[])
    def pure_func1(x: int) -> int: ...

    @guppy(max_effects=[])
    def pure_func2(x: int) -> int:
        return pure_func1(pure_func1(x))

    validate(pure_func2.compile_function())


def test_pure_from_impure(validate):
    @guppy(max_effects=[])
    def pure_func(x: int) -> int:
        return x

    @guppy
    def normal_func(x: int) -> int:
        return pure_func(x) + 1

    validate(normal_func.compile_function())


def test_pure_from_pure(validate):
    @guppy(max_effects=[])
    def pure_func1(x: int) -> int:
        return x

    @guppy(max_effects=[])
    def pure_func2(x: int) -> int:
        return pure_func1(pure_func1(x))

    validate(pure_func2.compile_function())
