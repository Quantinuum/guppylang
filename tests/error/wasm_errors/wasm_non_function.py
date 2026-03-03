from guppylang import guppy
from guppylang_internals.decorator import wasm, wasm_module

from tests.util import get_wasm_file

@wasm_module(get_wasm_file())
class Foo:
    @wasm
    def non_fn(self: "Foo") -> None: ...

@guppy
def main() -> qubit:
    mod = Foo(0)
    mod.non_fn()
    mod.discard
    return q

main.compile()
