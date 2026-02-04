from typing import Callable

from guppylang.decorator import guppy


@guppy.declare
def foo(f: "Callable[None]") -> None: ...


foo.compile()
