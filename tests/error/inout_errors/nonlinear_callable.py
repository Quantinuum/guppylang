from typing import Callable

from guppylang.decorator import guppy
from guppylang.std.builtins import owned


@guppy.declare
def foo(f: Callable[[int @owned], None]) -> None: ...


foo.compile()
