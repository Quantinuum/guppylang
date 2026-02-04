from guppylang import guppy
from guppylang.std.builtins import nat, comptime


@guppy.declare
def foo(n: nat @comptime) -> None: ...


@guppy
def main() -> None:
    foo(nat(1 + 2))


main.compile()
