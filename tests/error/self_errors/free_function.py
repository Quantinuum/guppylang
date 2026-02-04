from typing_extensions import Self

from guppylang.decorator import guppy


@guppy
def main(x: Self) -> None:
    pass


main.compile()
