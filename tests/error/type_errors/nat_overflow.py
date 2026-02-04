from guppylang.decorator import guppy
from guppylang.std.num import nat


@guppy
def foo() -> nat:
    return 18_446_744_073_709_551_616


foo.compile()
