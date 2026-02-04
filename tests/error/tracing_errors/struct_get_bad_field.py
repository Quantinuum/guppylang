from guppylang.decorator import guppy


@guppy.struct
class S:
    x: int


@guppy.comptime
def test(s: S) -> int:
    return s.y


test.compile()
