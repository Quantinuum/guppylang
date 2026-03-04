from guppylang import guppy
from typing import Generic
from tests.util import compile_guppy


T = guppy.type_var("T")

@guppy.enum
class Enum(Generic[T]):
    North = {"A": T}

@guppy.enum
class EnumGen(Generic[T]):
    Var = {"A": T}

@guppy.struct
class Point(Generic[T]):
    x: T
    y: int

@compile_guppy
def main() -> None:
    match Point(Enum.North(3), 5):
        case Point(EnumGen.Var(7), _):
            pass

