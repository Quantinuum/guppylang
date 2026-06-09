from guppylang.decorator import guppy


@guppy(dagger=True, control=True)
def test(i: int) -> None:
    while i < 46:
        pass


test.compile()
