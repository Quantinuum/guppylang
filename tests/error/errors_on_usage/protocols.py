from guppylang import guppy

@guppy.protocol
class Foo:
    @guppy.require
    def foo(self: "Foo") -> None: ...

@guppy
def bar(f: "Foo") -> None:
    return

@guppy.struct(frozen=True)
class FooStruct:
    @guppy
    def foo(self) -> None:
        return

@guppy
def main() -> None:
    bar(FooStruct())

main.check()
