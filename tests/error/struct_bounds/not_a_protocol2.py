"""Structs' bounds must be protocols.

In particular bounds such as `Copy` and `Drop` aren't valid bounds."""

from guppylang.decorator import guppy
from guppylang.std.builtins import nat
from guppylang.std.lang import Copy


@guppy.struct
class Bar(Copy):
    bar: nat

@guppy
def main() -> nat:
    x = Bar(0)
    return x.bar

main.compile()
