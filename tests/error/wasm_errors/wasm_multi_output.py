from guppylang import guppy
from guppylang_internals.decorator import wasm, wasm_module

from tests.util import get_wasm_file

@wasm_module(get_wasm_file())
class Foo:
    @wasm
    def multiple_outputs(self: "Foo") -> None: ...

@guppy
def main() -> qubit:
    mod = Foo(0)
    mod.multiple_outputs()
    mod.discard
    return q

main.compile()
