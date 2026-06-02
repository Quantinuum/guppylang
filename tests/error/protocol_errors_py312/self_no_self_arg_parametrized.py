from guppylang import guppy
from guppylang.std.builtins import nat

@guppy.protocol
class Foo[T]:
    @guppy.require
    def foo[T](t: T) -> None: ...

@guppy
def bar(f: Foo[nat]) -> None:
    return f.foo(42)

@guppy.struct
class Goo:
    @guppy
    def foo(n: nat) -> None:
        return

@guppy
def main() -> None:
    bar(Goo())

main.check()
