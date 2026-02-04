from guppylang.decorator import guppy
from tests.error.util import NonBool


@guppy
def foo(x: NonBool, y: bool) -> bool:
    return x and y


foo.compile()
