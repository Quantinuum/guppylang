from guppylang import guppy
from guppylang_internals.decorator import wasm, wasm_module
from guppylang_internals.wasm_util import WasmPlatform

from tests.util import get_h2_wasm_file

@wasm_module(get_h2_wasm_file(), WasmPlatform.H2)
class Foo:
    @wasm
    def multi(self: "Foo", x: int, y: int, z: int) -> int: ...

@guppy
def main() -> bool:
    f = Foo(0)
    return f.multi(1, 2)

main.compile()
