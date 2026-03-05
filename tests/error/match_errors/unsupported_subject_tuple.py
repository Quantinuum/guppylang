from tests.util import compile_guppy


@compile_guppy
def main(x: int, y: int) -> None:
    t = (x, y)
    match t:
        case _:
            pass
