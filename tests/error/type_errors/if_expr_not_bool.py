from guppylang.decorator import guppy
from tests.error.util import NonBool


@guppy
def foo(x: NonBool) -> int:
    return 1 if x else 0


foo.compile()
