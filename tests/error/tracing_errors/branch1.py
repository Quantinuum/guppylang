from guppylang.decorator import guppy


@guppy.comptime
def test(x: bool) -> int:
    return 1 if x else 0


test.compile()
