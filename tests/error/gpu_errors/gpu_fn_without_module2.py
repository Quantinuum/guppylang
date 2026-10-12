from guppylang import guppy
from guppylang_internals.decorator.gpu import gpu

@guppy.enum
class Foo:
    Var = {}
    @gpu
    def bar(self: "Foo") -> None: ...


@guppy
def main() -> None:
    mod = Foo.Var()
    mod.bar()
    mod.discard()
    return

main.compile()
