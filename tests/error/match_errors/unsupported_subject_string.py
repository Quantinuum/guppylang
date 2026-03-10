from tests.util import compile_guppy


@compile_guppy
def main() -> None:
    match "t":
        case _:
            pass
