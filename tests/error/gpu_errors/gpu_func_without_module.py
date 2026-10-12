from guppylang import guppy
from guppylang_internals.decorator.gpu import gpu, gpu_module

@gpu_module("module", "config")
class Foo:
    pass

@gpu
def foo(x: int) -> None: ...

@guppy
def main() -> None:
    mod = Foo()
    foo(mod)
    mod.discard()
    return

main.compile()
