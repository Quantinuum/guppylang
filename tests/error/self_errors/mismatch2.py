from typing_extensions import Self

from guppylang.decorator import guppy


@guppy.enum
class Foo:
    Var = {}
    @guppy
    def foo(self, other: Self) -> None:
        pass


@guppy
def main(f: Foo) -> None:
    f.foo(42)


main.compile()
