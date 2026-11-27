from guppylang import guppy


@guppy.struct
class S:
    value: float


@guppy
def main() -> None:
    S(0.0).value = 42


main.check()
