from guppylang.decorator import guppy


@guppy
def test() -> None:
    with power(1) as x:
        pass


test.compile()
