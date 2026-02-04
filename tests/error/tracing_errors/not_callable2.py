from guppylang.decorator import guppy

x = guppy._extern("x", "float")


@guppy.comptime
def test() -> None:
    x(1)


test.compile()
