from typing import Generic

from guppylang.decorator import guppy
from guppylang_internals.checker.core import V

T = guppy.type_var("T")


@guppy.enum
class Foo(Generic[T]):
    Var = {}

    @guppy
    def foo(my_self: int) -> None:
        pass


@guppy
def main(f: Foo[int]) -> None:
    f.foo()


main.compile()
