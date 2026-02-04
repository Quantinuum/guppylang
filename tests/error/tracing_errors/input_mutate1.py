from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned


@guppy.comptime
def foo(xs: array[int, 1] @ owned) -> None:
    xs[0] = 1


@guppy.comptime
def main() -> None:
    xs = [0]
    foo(xs)
    # Python users would expect xs to be mutated by the call above. However, we cannot
    # provide this semantics, so the mutation in `foo` is rejected by the compiler.


main.compile()
