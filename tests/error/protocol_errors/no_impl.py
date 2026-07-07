from guppylang import guppy
from guppylang.std.builtins import nat

@guppy.protocol
class Proto[T]:
    @guppy.require
    def foo(t: T) -> T: ...

@guppy
def bar[P: Proto[nat]](p: P, n: nat) -> nat:
    return p.foo(n)

@guppy
def baz() -> nat:
    return bar(nat, 42)

baz.compile()
