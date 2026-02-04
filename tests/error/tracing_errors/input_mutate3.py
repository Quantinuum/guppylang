from guppylang.decorator import guppy


@guppy.struct
class S:
    x: int


@guppy.comptime
def foo(s: S) -> None:
    s.x = 1


@guppy.comptime
def main() -> None:
    s = S(0)
    foo(s)
    # Python users would expect s to be mutated by the call above. However, we cannot
    # provide this semantics, so the mutation in `foo` is rejected by the compiler.


main.compile()
