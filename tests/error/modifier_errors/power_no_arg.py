from guppylang.decorator import guppy


@guppy
def test() -> None:
    with power():
        pass


test.compile()
