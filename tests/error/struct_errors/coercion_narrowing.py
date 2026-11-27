from guppylang import guppy


@guppy.struct
class S:
    value: int


@guppy
def main() -> None:
    s = S(0)
    s.value = 42.0


main.check()
