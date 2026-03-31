from guppylang import comptime
from guppylang.std.angles import angle
from tests.util import compile_guppy


@compile_guppy
def foo() -> int:
    return comptime(angle(0.5))
