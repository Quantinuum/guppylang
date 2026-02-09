from guppylang.decorator import guppy


@guppy
def test(b: bool) -> int:
    if b:
        x = 2



test.compile()
