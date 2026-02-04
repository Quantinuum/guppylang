from guppylang.decorator import guppy


@guppy.comptime
def test(x: float) -> float:
    return ~x


test.compile()
