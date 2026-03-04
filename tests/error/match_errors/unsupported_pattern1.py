from guppylang import guppy
from tests.util import compile_guppy


@guppy.struct
class Point:
    x: int
    y: int

@compile_guppy
def main(p: Point) -> None:
    match p:
        case Point(x, y):
            pass

