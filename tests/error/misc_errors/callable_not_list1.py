from guppylang.decorator import guppy
from guppylang.std.builtins import Fn


@guppy.declare
def foo(f: "Fn[int, float, bool]") -> None: ...


foo.compile()
