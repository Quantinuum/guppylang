from guppylang import guppy
from tests.util import compile_guppy

@guppy.struct
class Point:
    x: int
    y: int

@compile_guppy
def different_types(p: Point) -> int:
    result = 0
    match p:
        case Point(3, _):
            result = 3 
        case Point(_,_):
            result = True

    return result

