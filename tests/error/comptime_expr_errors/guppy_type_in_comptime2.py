from guppylang import guppy
from guppylang.std.builtins import comptime
from tests.util import compile_guppy

@guppy.enum
class Enum:
    VariantA = {"field": int}

@compile_guppy
def foo1() -> int:
    return comptime(Enum.VariantA(1))
