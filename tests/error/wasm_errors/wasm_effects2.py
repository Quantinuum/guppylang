from guppylang import guppy
from guppylang_internals.decorator.wasm import wasm, wasm_module
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit

from tests.util import get_wasm_file

@wasm_module(get_wasm_file())
class Foo:
    @wasm
    def two(self: "Foo") -> int: ...

@guppy(effects=[])
def dis(x: Foo @ owned) -> None:
    x.discard()

@guppy
def main() -> int:
    mod = Foo(0)
    q = mod.two()
    dis(mod)
    return q

main.compile()
