from guppylang import guppy
from guppylang_internals.decorator import wasm, wasm_module

@wasm_module("not_there.wasm")
class WasmModule:
    @wasm
    def foo(x: int) -> None: ...


@guppy
def main() -> None:
    foo(42)

main.compile()
