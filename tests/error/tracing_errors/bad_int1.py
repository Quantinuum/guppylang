from guppylang.decorator import guppy


@guppy.comptime
def test(x: int) -> int:
    # constant is smallest positive value that fails
    return x + (1 << 63)

test.compile()
