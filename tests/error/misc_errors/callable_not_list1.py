from collections.abc import Callable

from guppylang.decorator import guppy


@guppy.declare
def foo(f: "Callable[int, float, bool]") -> None: ...


foo.compile()
