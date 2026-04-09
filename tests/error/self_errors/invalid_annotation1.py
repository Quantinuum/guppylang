from typing import Generic

from guppylang.decorator import guppy

T = guppy.type_var("T")


@guppy.struct
class Foo(Generic[T]):
    @guppy
    def foo(my_self: int) -> None:
        pass


@guppy
def main(f: Foo[int]) -> None:
    f.foo()


main.compile()
