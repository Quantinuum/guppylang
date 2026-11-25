"""Structs' bounds must be protocols"""

from guppylang.decorator import guppy
from guppylang.std.builtins import nat


@guppy.struct
class Foo:
    @guppy
    def foo(self) -> nat:
        return 0


@guppy.struct
class Bar(Foo):
    @guppy
    def foo(self) -> nat:
        return 0


@guppy
def main() -> nat:
    x = Bar()
    return x.foo()


main.compile()
