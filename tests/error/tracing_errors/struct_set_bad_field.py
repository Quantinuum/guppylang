from guppylang.decorator import guppy


@guppy.struct
class S:
    x: int


@guppy.comptime
def test(x: int) -> None:
    s = S(x)
    s.y = x


test.compile()
