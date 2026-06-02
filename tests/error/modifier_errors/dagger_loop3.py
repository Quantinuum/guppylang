from guppylang.decorator import guppy

from tests.integration.test_modifier import dagger

@guppy
def test() -> None:
    with dagger:
        with dagger:
            ok = [i for i in range(46)]
        x = [i for i in range(46)]

test.compile()
