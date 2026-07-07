from guppylang.std.builtins import output
from tests.util import compile_guppy


@compile_guppy
def foo(x: int) -> None:
    output((), x)
