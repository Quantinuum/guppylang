from guppylang import comptime
from guppylang.std.builtins import array
from tests.util import compile_guppy


@compile_guppy
def foo(xs: array[int, comptime(1.0)]) -> None:
    pass
