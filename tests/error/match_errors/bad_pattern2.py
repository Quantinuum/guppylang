from guppylang import guppy
from tests.util import compile_guppy

@guppy.enum
class Enum:
    North = {"A": int}

    @guppy
    def method(self) -> str:
        return "Direction"

@compile_guppy
def main(north: Enum, x: int) -> None:
    match north:
        case north.method():
            pass

