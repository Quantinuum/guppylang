from guppylang.decorator import guppy
from guppylang.std.builtins import Function


@guppy.declare
def foo(f: "Function[int, float, bool]") -> None: ...


foo.compile()
