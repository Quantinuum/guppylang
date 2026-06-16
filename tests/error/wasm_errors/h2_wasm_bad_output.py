from guppylang import guppy, qubit
from guppylang_internals.decorator.wasm import wasm, wasm_module
from guppylang_internals.std._internal.wasm import WasmPlatform

from tests.util import get_wasm_file

@wasm_module(get_wasm_file(), WasmPlatform.H2)
class Foo:
    @wasm
    def two(self: "Foo") -> int: ...


@guppy
def main() -> qubit:
    mod = Foo(0)
    mod.two()
    mod.discard
    return qubit()

main.compile()
