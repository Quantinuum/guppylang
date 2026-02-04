from guppylang.decorator import guppy


@guppy
def test() -> None:
    with True:
        pass


test.compile()
