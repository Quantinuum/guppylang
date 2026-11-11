from tests.util import compile_guppy


@compile_guppy
def no_return_if_not(b: bool) -> int:
    if not b:
        return 0
