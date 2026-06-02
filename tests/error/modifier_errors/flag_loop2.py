from guppylang.decorator import guppy


@guppy(dagger=True)
def test(i: int) -> None:
    while i < 46:
        pass


test.compile()
