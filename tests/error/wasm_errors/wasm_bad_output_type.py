from guppylang import guppy
from guppylang_internals.decorator import wasm, wasm_module
from guppylang.module import GuppyModule

from tests.util import get_wasm_file

@wasm_module(get_wasm_file())
class Foo:
    @wasm
    def add(self: "Foo", x: int, y: int) -> bool: ...

@guppy
def main() -> bool:
    f = Foo(0)
    return f.add(1, 2)

main.compile()
