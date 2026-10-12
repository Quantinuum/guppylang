from tests.util import compile_guppy


@compile_guppy
def no_return_loop_walrus_not(b: bool) -> int:
    while not (b := b):
        return 0
