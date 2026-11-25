from guppylang import guppy


@guppy.struct
class Foo:
    @guppy.require
    def foo(self: "Foo") -> None: ...


Foo.compile()
