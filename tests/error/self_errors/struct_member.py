from typing_extensions import Self

from guppylang.decorator import guppy


@guppy.struct
class Foo:
    x: Self


@guppy
def main(f: Foo) -> None:
    pass


main.compile()
