from guppylang import guppy
from guppylang_internals.decorator import wasm, wasm_module

from tests.util import get_wasm_file

@wasm_module(get_wasm_file())
class WasmModule:
    @wasm
    def nothing() -> int: ...


@guppy
def main() -> None:
    mod = WasmModule(0)
    mod.nothing()
    mod.discard()
    return

main.compile()
