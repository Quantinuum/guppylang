from tests.util import compile_guppy


@compile_guppy
def main() -> None:
    n = None
    match n:
        case _:
            pass
