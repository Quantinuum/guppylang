from guppylang.decorator import guppy


@guppy.comptime
def test(x: int) -> int:
    return (1, 2) + x


test.compile()
