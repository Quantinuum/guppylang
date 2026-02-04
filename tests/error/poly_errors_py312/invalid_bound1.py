from guppylang.decorator import guppy


@guppy
def main[x: 42]() -> None:
    ...


main.compile()
