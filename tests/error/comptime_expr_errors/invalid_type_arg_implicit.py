from guppylang.std.builtins import array
from tests.util import compile_guppy


a = 1.0

@compile_guppy
def foo(xs: array[int, a]) -> None:
    pass
