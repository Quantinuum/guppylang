from guppylang.decorator import guppy


@guppy.struct
class S:
    x: int


@guppy.comptime
def test() -> S:
    s = S(1)
    s.x = 1.0
    return s


test.compile()
