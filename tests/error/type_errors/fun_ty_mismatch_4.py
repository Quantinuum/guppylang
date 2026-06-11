from collections.abc import Callable

from guppylang.std.builtins import nat

from tests.util import compile_guppy


@compile_guppy
def foo() -> Callable[[nat], int]:
    # This has a narrower return type, but we enforce invariance of Callable types, so this is still an error.
    def bar(x: nat) -> nat:
        return x

    return bar
