from guppylang.decorator import guppy


@guppy(daggerable=True)
def test() -> None:
    for _ in range(10):
        pass


test.compile()
