from guppylang.decorator import guppy


@guppy.comptime
def test(x: int) -> int:
    return x + (2, 3)


test.compile()
