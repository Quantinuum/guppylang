from guppylang import guppy
from guppylang.std.quantum import qubit, owned
from tests.util import compile_guppy

@guppy.struct
class Point:
    x: qubit
    y: int


@compile_guppy
def main(p: Point @owned) -> None: # pyright: ignore[reportInvalidTypeForm]
    match p:
        case Point(_, _):
            b = p.x

