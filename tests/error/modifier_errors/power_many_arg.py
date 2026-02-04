from guppylang.decorator import guppy


@guppy
def test() -> None:
    with power(1, 2, 3):
        pass


test.compile()
