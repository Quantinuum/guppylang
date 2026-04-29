from guppylang.decorator import guppy
from guppylang.std.num import nat


@guppy.enum
class Foo[T]:
    Var = {}
    
    @guppy
    def foo[T: nat](my_self) -> None:   # Shadow
        pass


@guppy
def main(f: Foo[int]) -> None:
    f.foo()


main.compile()
