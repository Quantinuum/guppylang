from guppylang.decorator import guppy
from guppylang.std.num import nat


@guppy
def foo() -> nat:
    return -1


foo.compile()
