from guppylang import guppy
from tests.util import compile_guppy


@guppy.enum
class Enum:
    North = {"a": int, "b": int}

@compile_guppy
def main(p: Enum, x: int) -> None:
    match p:
        case Enum.North(_):
            z = 66

