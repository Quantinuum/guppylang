from guppylang.decorator import guppy


@guppy
def test() -> None:
    with dagger(1):
        pass


test.compile()
