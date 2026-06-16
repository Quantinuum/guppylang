from guppylang.decorator import guppy


@guppy.protocol
class MyProto:

    var = 42

    @guppy.require
    def foo(self: "MyProto", x: int) -> str: ...


MyProto.compile()
