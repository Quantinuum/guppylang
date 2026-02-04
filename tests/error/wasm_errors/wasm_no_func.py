from guppylang import guppy
from guppylang_internals.decorator import wasm, wasm_module

from tests.util import get_wasm_file

@wasm_module(get_wasm_file())
class MyWasm:
    @wasm
    def foo(self: "MyWasm") -> None: ...


@guppy
def main() -> None:
    mod = MyWasm(0)
    mod.foo()
    mod.discard()


main.compile()
