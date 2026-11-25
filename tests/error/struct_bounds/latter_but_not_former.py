"""Protocol validation fails if one of multiple bounds fails to validate.

This is the case where the second bound is met but not the first."""
from guppylang.decorator import guppy
from guppylang.std.builtins import nat


@guppy.protocol
class Foo:
    @guppy.require
    def foo(self) -> nat: ...


@guppy.protocol
class Oof:
    @guppy.require
    def oof(self) -> nat: ...


@guppy.struct
class Bar(Oof, Foo):
    @guppy
    def foo(self) -> nat:
        return 0


@guppy
def main() -> nat:
    x = Bar()
    return x.foo()


main.compile()
