from guppylang.std.lang import Function
from tests.util import compile_guppy


@compile_guppy
def foo() -> None:
    f: Function[[], None] = len
