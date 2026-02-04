from guppylang import guppy
from guppylang.std.builtins import nat, comptime


@guppy.declare
def foo(n: nat @comptime) -> None: ...


@guppy
def main(b: bool, m: nat) -> None:
    if b:
        foo(m)


main.compile_function()
