from guppylang.decorator import guppy


@guppy.protocol
class MyProto(metaclass=type):
    @guppy.require
    def foo(self: "MyProto", x: int) -> str: ...


MyProto.compile()
