from guppylang import guppy
from guppylang_internals.decorator import wasm

@guppy.struct
class Foo:
    @wasm
    def bar(self: "Foo") -> None: ...


@guppy
def main() -> None:
    mod = Foo()
    mod.bar()
    mod.discard()
    return

main.compile()
