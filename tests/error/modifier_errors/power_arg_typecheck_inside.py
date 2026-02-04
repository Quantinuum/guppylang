from guppylang.decorator import guppy


@guppy
def test() -> None:
    with power(12 + False):
        pass


test.compile()
