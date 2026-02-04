from guppylang.decorator import guppy


@guppy
def test() -> None:
    with dagger:
        return


test.compile()
