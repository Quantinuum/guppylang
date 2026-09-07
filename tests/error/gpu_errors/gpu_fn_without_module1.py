from guppylang import guppy
from guppylang_internals.decorator.gpu import gpu

@guppy.struct
class Foo:
    @gpu
    def bar(self: "Foo") -> None: ...


@guppy
def main() -> None:
    mod = Foo()
    mod.bar()
    mod.discard()
    return

main.compile()
