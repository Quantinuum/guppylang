from guppylang.decorator import guppy
from tests.error.util import NonBool


@guppy
def foo(x: NonBool) -> int:
    if x:
        return 0
    return 1


foo.compile()
