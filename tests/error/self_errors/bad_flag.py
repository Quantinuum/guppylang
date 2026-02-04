from typing_extensions import Self

from guppylang.decorator import guppy
from guppylang.std.lang import owned


@guppy.struct
class Foo:
    @guppy
    def foo(self: Self @owned) -> None:
        pass


@guppy
def main(f: Foo) -> None:
    f.foo()


main.compile()
