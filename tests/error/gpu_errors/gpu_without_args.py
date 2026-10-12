from guppylang import guppy
from guppylang_internals.decorator.gpu import gpu_module, gpu


@gpu_module("module", "config")
class GpuModule:
    @gpu
    def nothing() -> int: ...


@guppy
def main() -> None:
    mod = GpuModule()
    mod.nothing()
    mod.discard()
    return

main.compile()
