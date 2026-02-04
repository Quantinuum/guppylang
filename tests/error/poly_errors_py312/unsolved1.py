from guppylang.decorator import guppy


@guppy
def foo[x: bool]() -> bool:
    return x


@guppy
def main() -> bool:
    return foo()


main.compile()
