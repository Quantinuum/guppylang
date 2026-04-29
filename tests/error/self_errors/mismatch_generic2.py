from typing import Generic

from guppylang.decorator import guppy

T = guppy.type_var("T")


@guppy.enum
class Foo(Generic[T]):
    Var = {}
    @guppy
    def foo(self, x: T) -> None:
        pass


@guppy
def main(f: Foo[int]) -> None:
    f.foo(1.5)


main.compile()