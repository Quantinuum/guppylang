from guppylang import guppy
from hugr.std.float import FloatVal

x = guppy.constant("x", "float", FloatVal(4.2))


@guppy
def main(b: bool) -> None:
    if b:
        x = 1.0

    def inner() -> float:
        return x


main.compile_function()
