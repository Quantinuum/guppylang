from guppylang.decorator import guppy


@guppy.declare
def foo() -> None: ...


@guppy.comptime
def test() -> None:
    foo[0]()


test.compile()
