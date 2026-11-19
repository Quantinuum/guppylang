"""Protocol validation fails if the struct has the same methods but with the
   wrong type."""

from guppylang.decorator import guppy
from guppylang.std.builtins import nat


@guppy.protocol
class Foo:
    @guppy.require
    def foo(self) -> nat: ...


@guppy.struct
class Bar(Foo):
    @guppy
    def foo(self) -> bool:
        return True


@guppy
def main() -> nat:
    x = Bar()
    x.foo()
    return 0


main.compile()
