from guppylang.decorator import guppy


@guppy.declare
def foo(x: int) -> int: ...


@guppy.comptime
def test() -> None:
    foo(set())


test.compile()
