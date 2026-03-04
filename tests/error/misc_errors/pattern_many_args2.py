from guppylang import guppy
from tests.util import compile_guppy


@guppy.enum
class Enum:
    North = {"A": int}

@compile_guppy
def main(p: Enum, x: int) -> None:
    match p:
        case Enum.North(1,2):
            z = 66

