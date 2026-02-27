"""More complicated expressions of imports that should not affect retaining them in
stubs."""

from guppylang import guppy, comptime
from guppylang.std.quantum import qubit, discard
from guppylang.std.num import nat
from guppylang.std.lang import owned


# Currently ignored, since we do not support type unions yet
# @guppy
def _lib_func_or_none(x: int | None) -> None:
    pass


@guppy
def lib_func_comptime_arg(x: nat @ comptime) -> None:
    pass


@guppy
def lib_func_owned_arg(x: qubit @ owned) -> None:
    discard(x)
