from guppylang import guppy
from guppylang_internals.decorator import wasm, wasm_module

from tests.util import get_wasm_file

@wasm_module(get_wasm_file())
class Foo:
    @wasm
    def bad_input_type(self: "Foo", x: int) -> None: ...

@guppy
def main() -> qubit:
    mod = Foo(0)
    mod.bad_input_type(42)
    mod.discard
    return q

main.compile()
