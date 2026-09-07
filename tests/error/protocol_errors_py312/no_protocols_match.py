from guppylang import guppy
from guppylang.std.builtins import nat

@guppy.protocol
class FooNat:
    @guppy.require
    def foo(self, n: nat) -> nat: ...

@guppy.protocol
class FooInt:
    @guppy.require
    def foo(self, n: int) -> int: ...

@guppy.struct(frozen=True)
class Foo:
    @guppy
    def foo[T: (Copy, Drop)](self, n: T) -> T:
        return n

@guppy
def bar_flt[T: (FooNat, FooInt)](t: T, n: float) -> nat:
    return t.foo(n)

@guppy
def main() -> None:
    bar_flt(Foo(), 42)
    return


main.compile()
