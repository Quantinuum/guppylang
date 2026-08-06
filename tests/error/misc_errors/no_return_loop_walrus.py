from tests.util import compile_guppy

@compile_guppy
def while_loop(b: bool) -> int:
    while (b := b):
        return 0