from guppylang.decorator import guppy
from guppylang.std.builtins import Function


@guppy.declare
def foo(f: Function) -> None: ...


foo.compile()
