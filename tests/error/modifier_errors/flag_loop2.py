from guppylang.decorator import guppy


@guppy(daggerable=True, controllable=True)
def test(i: int) -> None:
    while i < 46:
        pass


test.compile()
