from guppylang.decorator import guppy


@guppy
def test() -> None:
    with dagger:
        for _ in range(46):
            pass


test.compile()
