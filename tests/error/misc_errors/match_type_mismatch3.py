from typing import Generic
from tests.util import compile_guppy
from guppylang import guppy


T = guppy.type_var("T")

@guppy.struct
class Point(Generic[T]):
    A: T

@compile_guppy
def main(d: Point[T]) -> None:
    match d:
        case Point(1):
            pass

