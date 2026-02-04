from guppylang.std.builtins import panic
from tests.util import compile_guppy


@compile_guppy
def foo(x: int) -> None:
    panic((), x)
