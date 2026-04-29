from typing import Generic
from typing_extensions import Self

from guppylang.decorator import guppy

T = guppy.type_var("T")


@guppy.enum
class Foo(Generic[T]):
    Var = {}
    @guppy
    def foo(self: "Self[int]") -> None:
        pass


@guppy
def main(f: Foo[int]) -> None:
    f.foo()


main.compile()
