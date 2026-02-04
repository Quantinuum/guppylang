from guppylang import guppy
from guppylang.std.builtins import comptime, nat


@guppy
def foo(n: nat @ comptime) -> None:
    pass


@guppy
def main() -> None:
    foo(False)


main.compile()
