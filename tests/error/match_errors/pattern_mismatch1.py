from guppylang import guppy
from tests.util import compile_guppy

@guppy.enum
class Enum:
    North = {"A": int}

@guppy.struct
class Point:
    x: int

@compile_guppy
def main(north: Enum) -> None:
    match north:
        case Point(1):
            pass

