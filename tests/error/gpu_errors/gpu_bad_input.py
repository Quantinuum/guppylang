from guppylang import guppy
from guppylang_internals.decorator.gpu import gpu, gpu_module


@gpu_module("module", "config")
class Foo:
    @gpu
    def bad_input_type(self: "Foo", x: bool) -> None: ...

@guppy
def main() -> None:
    mod = Foo()
    mod.bad_input_type(True)
    mod.discard()
    return

main.compile()
