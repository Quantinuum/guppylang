from guppylang import guppy
from guppylang.std.builtins import nat, comptime


@guppy.declare
def foo(n: nat @comptime) -> None: ...


@guppy
def main() -> None:
    m: nat = 1
    foo(m)


main.compile()
