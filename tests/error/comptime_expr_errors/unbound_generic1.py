from guppylang import guppy
from guppylang.std.builtins import comptime

n = guppy.nat_var("n")


@guppy
def main() -> None:
    x = comptime(n)


main.compile()
