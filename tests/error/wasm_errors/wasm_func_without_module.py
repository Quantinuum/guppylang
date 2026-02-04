from guppylang import guppy
from guppylang_internals.decorator import wasm, wasm_module

from tests.util import get_wasm_file

@wasm_module(get_wasm_file())
class Foo:
    pass

@wasm
def foo(x: int) -> None: ...

@guppy
def main() -> None:
    mod = Foo(0)
    foo(mod)
    mod.discard()
    return

main.compile()
