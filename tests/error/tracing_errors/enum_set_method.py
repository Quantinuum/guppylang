import re

from guppylang.decorator import guppy


@guppy.enum
class E:
    A = {}  # noqa: RUF012

    @guppy
    def foo(self: "E") -> int:
        return 42

@guppy
def bar(e: E) -> int:
    return 42

@guppy.comptime
def test() -> None:
    e = E.A()
    e.foo = bar


test.compile()
