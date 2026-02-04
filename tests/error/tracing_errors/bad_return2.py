from guppylang.decorator import guppy


@guppy.comptime
def test() -> int:
    if True:
        return 1.0
    else:
        return 1


test.compile()
