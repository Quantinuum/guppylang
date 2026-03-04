from guppylang import guppy
from tests.util import compile_guppy


@guppy.enum
class Enum:
    f = {"m": int}
    Var = {}

@compile_guppy
def main(i: Enum) -> None:
    match i:
        case Enum.f.m():
            pass
        

