from guppylang.decorator import guppy
from guppylang.std.builtins import owned, Function


@guppy.declare
def foo(f: Function[[int @ owned], None]) -> None: ...


foo.compile()
