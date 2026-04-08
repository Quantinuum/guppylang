"""More complicated expressions of imports that should not affect retaining them in
stubs."""
from guppylang import guppy, comptime
from guppylang.std.quantum import qubit
from guppylang.std.num import nat
from guppylang.std.lang import owned

@guppy.declare
def lib_func_comptime_arg(x: nat @ comptime) -> None:
    ...

@guppy.declare
def lib_func_owned_arg(x: qubit @ owned) -> None:
    ...