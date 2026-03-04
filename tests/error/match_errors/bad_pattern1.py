from tests.util import compile_guppy
from guppylang import guppy

@guppy.enum
class Enum:
    North = {"A": int}

@guppy
def g() -> Enum:
    return Enum.North(5)

@compile_guppy
def main(north: Enum) -> None:
    match north:
        case g():  # ERROR: match on a function
            pass


