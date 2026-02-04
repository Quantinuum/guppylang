from guppylang.decorator import guppy


@guppy.comptime
def test(n: int) -> int:
    s = 0
    for i in range(n):
        s += 1
    return s


test.compile()
