from guppylang.decorator import guppy
from guppylang.std.builtins import owned, Fn


@guppy.declare
def foo(f: Fn[[int @owned], None]) -> None: ...


foo.compile()
