from guppylang.decorator import guppy


@guppy.struct
class S:
    x: int


@guppy.declare
def foo(s: S) -> None: ...


@guppy.comptime
def test() -> None:
    s = S(1)
    s.x = 1.0
    foo(s)


test.compile()
