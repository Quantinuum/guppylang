from guppylang.decorator import guppy


@guppy
def test() -> None:
    with power(0.3):
        pass


test.compile()
