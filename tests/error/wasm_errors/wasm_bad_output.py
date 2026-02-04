from guppylang import guppy
from guppylang_internals.decorator import wasm, wasm_module

from tests.util import get_wasm_file

@wasm_module(get_wasm_file())
class Foo:
    @wasm
    def bad_output_type(self: "Foo") -> float: ...

@guppy
def main() -> qubit:
    mod = Foo(0)
    f = mod.bad_output_type()
    mod.discard
    return q

main.compile()
