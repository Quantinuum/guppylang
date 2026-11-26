from guppylang import guppy


@guppy.protocol
class Foo:
    @guppy.declare
    def foo(self: "Foo") -> None: ...


Foo.compile()
