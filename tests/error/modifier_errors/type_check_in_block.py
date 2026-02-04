from guppylang.decorator import guppy


@guppy
def test() -> None:
    with dagger:
        1 + True


test.compile()
