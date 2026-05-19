from guppylang import guppy

@guppy.protocol
class Foo[T]:
    @guppy.require
    def foo[T](self: "Foo[T]", x: T) -> T: ...

@guppy.protocol
class FooInt:
    @guppy.require
    def foo[T](self: "FooInt", x: int) -> int: ...

@guppy.struct
class Bar:
    @guppy
    def foo(self, x: int) -> int:
        return

@guppy
def eat_foostr(f: Foo[str]) -> None:
    return

@guppy
def baz(f: FooInt) -> None:
    return eat_foostr(f)

@guppy
def main() -> None:
    b = Bar()
    baz(b)

main.check()
