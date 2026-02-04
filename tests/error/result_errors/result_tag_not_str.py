from guppylang.std.builtins import result
from tests.util import compile_guppy


@compile_guppy
def foo(x: int) -> None:
    result((), x)
