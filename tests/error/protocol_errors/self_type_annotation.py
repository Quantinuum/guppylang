from guppylang import guppy
from typing import Self

@guppy.protocol
class Foo:
    @guppy.require
    def foo(self: Self) -> None: ...

@guppy.struct
class Goo:
    @guppy
    def foo(self) -> None:
        return

@guppy
def bar(f: Foo) -> None:
    return f.foo()

@guppy
def main() -> None:
    f = Goo()
    return bar(f)

main.check()
