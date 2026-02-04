from typing import Generic

from guppylang.decorator import guppy

T = guppy.type_var("T")


@guppy.struct
class Foo(Generic[T]):
    @guppy
    def foo(self, x: T) -> None:
        pass


@guppy
def main(f: Foo[int]) -> None:
    f.foo(1.5)


main.compile()