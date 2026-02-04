from guppylang.decorator import guppy


@guppy.comptime
def test(x: float) -> None:
    x(1)


test.compile()
