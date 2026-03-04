from guppylang import guppy
from tests.util import compile_guppy

@guppy.enum
class Enum:
    North = {}
    South = {}


@compile_guppy
def main(x: int, a: int) -> None:
    match x:
        case Enum.North() | Enum.South():
            pass

