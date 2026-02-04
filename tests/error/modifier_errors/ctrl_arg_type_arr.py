from guppylang.decorator import guppy


@guppy
def test() -> None:
    x = array(1, 2, 3)
    with control(x):
        pass


test.compile()
