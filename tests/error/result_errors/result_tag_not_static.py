from guppylang.std.builtins import result
from tests.util import compile_guppy


@compile_guppy
def foo(y: bool, x: int) -> None:
    result("foo" if y else "bar", x)
