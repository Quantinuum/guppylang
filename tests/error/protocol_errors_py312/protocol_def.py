from guppylang import guppy

@guppy.protocol
class Foo:
    @guppy
    def foo(self: "Foo") -> None: ...

@guppy.struct
class Foo2:
    @guppy
    def foo(self) -> None:
        return

@guppy
def bar[F: Foo](f: F) -> None:
    return f.foo()


@guppy
def main() -> None:
    bar(Foo2())
    return

main.compile()
