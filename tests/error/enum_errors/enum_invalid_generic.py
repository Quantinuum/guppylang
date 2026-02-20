from typing import Generic, TypeVar

from guppylang.decorator import guppy


X = TypeVar("X")  # This is a Python type variable, not a Guppy one!


@guppy.enum
class MyEnum(Generic[X]):
    var = {"x": int}


MyEnum.compile()
