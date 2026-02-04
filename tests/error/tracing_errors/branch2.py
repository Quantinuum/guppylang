from guppylang.decorator import guppy


@guppy.declare
def foo() -> int: ...


@guppy.comptime
def test() -> int:
    if foo() > 1:
        return 1
    return 0


test.compile()
