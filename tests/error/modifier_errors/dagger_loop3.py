from guppylang.decorator import guppy


@guppy(dagger=True)
def test() -> None:
    x = [i for i in range(46)]

test.compile()
