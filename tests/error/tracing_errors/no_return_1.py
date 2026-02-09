from guppylang.decorator import guppy


@guppy.comptime
def test() -> int:
    pass


test.compile()
