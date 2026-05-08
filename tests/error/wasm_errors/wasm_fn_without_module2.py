from guppylang import guppy
from guppylang_internals.decorator import wasm

@guppy.enum
class Foo:
    Var = {}
    @wasm
    def bar(self: "Foo") -> None: ...


@guppy
def main() -> None:
    mod = Foo.Var()
    mod.bar()
    mod.discard()
    return

main.compile()
