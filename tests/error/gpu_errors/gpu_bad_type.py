from guppylang import guppy
from guppylang_internals.decorator.gpu import gpu, gpu_module

from guppylang.std.quantum import qubit

@gpu_module("module", "config")
class Foo:
    @gpu
    def two(self: "Foo", x: qubit) -> qubit: ...

@guppy
def main() -> qubit:
    mod = Foo()
    q = mod.two(qubit())
    mod.discard()
    return q

main.compile()
