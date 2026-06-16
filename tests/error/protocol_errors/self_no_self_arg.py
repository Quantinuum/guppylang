from guppylang import guppy
from guppylang.std.builtins import nat

@guppy.protocol
class Foo:
    @guppy.require
    def foo(n: nat) -> None: ...

@guppy
def bar(f: Foo) -> None:
    return f.foo(42)

@guppy.struct(frozen=True)
class Goo:
    @guppy
    def foo(n: nat) -> None:
        return

@guppy
def main() -> None:
    bar(Goo())

main.check()
