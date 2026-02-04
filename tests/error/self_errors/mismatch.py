from typing_extensions import Self

from guppylang.decorator import guppy


@guppy.struct
class Foo:
    @guppy
    def foo(self, other: Self) -> None:
        pass


@guppy
def main(f: Foo) -> None:
    f.foo(42)


main.compile()
