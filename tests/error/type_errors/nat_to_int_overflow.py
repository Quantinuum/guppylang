from guppylang.decorator import guppy
from guppylang.std.num import nat


@guppy
def foo() -> int:
    return int(nat(9_223_372_036_854_775_808))


foo.compile()
