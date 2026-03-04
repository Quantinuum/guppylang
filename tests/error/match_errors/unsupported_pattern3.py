from tests.util import compile_guppy


@compile_guppy
def main(x: int, a: int) -> None:
    match x:
        case _ if a > 0:
            pass

