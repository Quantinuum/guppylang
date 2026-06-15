"""Struct definitions used to test imported type-dependency scopes."""

from guppylang.decorator import guppy


@guppy.struct
class B:
    x: int


@guppy.struct
class A:
    b: B
