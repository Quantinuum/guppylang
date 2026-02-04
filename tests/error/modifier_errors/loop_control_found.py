from guppylang.decorator import guppy


@guppy
def test() -> None:
    for i in range(123):
        with dagger:
            continue


test.compile()
