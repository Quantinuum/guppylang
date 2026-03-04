from guppylang import guppy
from tests.util import compile_guppy


@guppy.enum
class Enum:
    North = {"q": int}

@compile_guppy
def f(e: Enum) -> None:
    match e:
        case Enum.North:
            pass

