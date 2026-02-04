from guppylang.decorator import guppy


@guppy.comptime
def test(x: int) -> int:
    # constant is largest negative value that fails
    return x + (-(1 << 63) - 1)

test.compile()
