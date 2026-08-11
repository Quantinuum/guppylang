from guppylang.std.builtins import output
from tests.util import compile_guppy


@compile_guppy
def foo(y: bool, x: int) -> None:
    output("foo" if y else "bar", x)
