from guppylang.decorator import guppy


@guppy
def f(x: int) -> int:
    return x


@guppy
def g(x: int) -> int:
    return x


@guppy
def main() -> tuple[int, int]:
    return (f, g)(1, 2)


main.compile()
