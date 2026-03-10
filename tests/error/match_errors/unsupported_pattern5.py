from guppylang import guppy
from tests.util import compile_guppy

@guppy.enum
class Enum:
    North = {"s": str}
    South = {}


@compile_guppy
def main(x: Enum) -> None:
    match x:
        case Enum.North("fail"):
            pass

