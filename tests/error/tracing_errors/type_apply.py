from guppylang.decorator import guppy


T = guppy.type_var("T")


@guppy.declare
def foo(x: T) -> T: ...


@guppy.comptime
def test() -> int:
    return foo[int](0)


test.compile()
