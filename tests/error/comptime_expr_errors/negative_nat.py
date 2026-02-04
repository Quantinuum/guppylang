from guppylang.std.builtins import nat
from tests.util import compile_guppy


@compile_guppy
def foo() -> nat:
    return comptime(-1)
