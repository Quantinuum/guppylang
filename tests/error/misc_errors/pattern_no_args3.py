from guppylang import guppy
from tests.util import compile_guppy


@guppy.struct
class Point:
    x: int
    y: int

@compile_guppy
def main(p: Point, x: int) -> None:
    match p:
        case Point(_):
            z = 66

