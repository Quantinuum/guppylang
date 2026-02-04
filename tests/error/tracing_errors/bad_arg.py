from guppylang.decorator import guppy


@guppy.declare
def foo(x: int) -> None: ...


@guppy.comptime
def test() -> None:
    foo(1.0)


test.compile()
