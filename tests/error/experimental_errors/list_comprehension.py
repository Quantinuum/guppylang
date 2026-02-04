from guppylang.decorator import guppy


@guppy
def main() -> None:
    [i for i in range(10)]


main.compile()
