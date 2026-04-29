from typing_extensions import Self

from guppylang.decorator import guppy
from guppylang.std.num import nat


@guppy.enum
class Foo[T]:
    Var = {}
    
    @guppy
    def foo[T: nat](self: Self) -> None:   # Shadow
        pass


@guppy
def main(f: Foo[int]) -> None:
    f.foo()


main.compile()
