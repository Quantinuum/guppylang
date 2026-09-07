from guppylang import guppy
from guppylang_internals.decorator.gpu import gpu, gpu_module


@gpu_module("module", "config")
class Foo:
    @gpu
    def bad_output_type(self: "Foo") -> bool: ...

@guppy
def main() -> None:
    mod = Foo()
    f = mod.bad_output_type()
    mod.discard()
    return

main.compile()
