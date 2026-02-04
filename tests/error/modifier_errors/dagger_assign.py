from guppylang.decorator import guppy


@guppy
def test() -> None:
    with dagger:
        a = 3


test.compile()
