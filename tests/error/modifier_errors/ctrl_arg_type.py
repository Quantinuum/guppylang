from guppylang.decorator import guppy


@guppy
def test() -> None:
    x = qubit()
    with control(x, True):
        pass


test.compile()
