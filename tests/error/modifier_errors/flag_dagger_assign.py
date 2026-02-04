from guppylang.decorator import guppy


@guppy(dagger=True)
def test() -> None:
    x = 3


test.compile()
