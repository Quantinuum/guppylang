from guppylang import guppy


@guppy(dagger=True)
def test() -> None:
    x = 3


test.compile()
