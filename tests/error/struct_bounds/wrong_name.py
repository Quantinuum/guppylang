"""Protocol validation fails if the struct doesn't have the methods required
by the protocol."""

from guppylang.decorator import guppy
from guppylang.std.builtins import nat


@guppy.protocol
class Foo:
    @guppy.require
    def foo(self) -> nat: ...


@guppy.struct
class Bar(Foo):
    @guppy
    def bar(self) -> nat:
        return 0


@guppy
def main() -> nat:
    x = Bar()
    return x.bar()


main.compile()
