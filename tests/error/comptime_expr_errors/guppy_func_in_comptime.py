from guppylang import comptime
from guppylang.decorator import guppy
from tests.util import compile_guppy


@guppy
def my_func() -> int:
    return 42


@compile_guppy
def foo() -> int:
    return comptime(my_func())
