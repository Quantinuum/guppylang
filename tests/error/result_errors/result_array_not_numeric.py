from guppylang.std.builtins import result, array
from tests.util import compile_guppy


@compile_guppy
def foo(x: array[tuple[int, bool], 42]) -> None:
    result("foo", x)
