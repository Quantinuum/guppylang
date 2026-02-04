from guppylang import guppy
from guppylang.std.builtins import nat

n = guppy.nat_var("n")


@guppy
def main(b: bool) -> nat:
    if b:
        n = nat(42)
    return n


main.compile_function()
