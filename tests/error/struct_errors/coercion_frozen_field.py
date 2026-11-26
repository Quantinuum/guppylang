from guppylang import guppy


@guppy.struct(frozen=True)
class S:
    value: float


@guppy
def main() -> None:
    s = S(0.0)
    s.value = 42


main.check()
