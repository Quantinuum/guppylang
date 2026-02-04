from guppylang.decorator import guppy


@guppy
def main() -> None:
    [1, 2, 3]


main.compile()
