from guppylang.decorator import guppy

@guppy.protocol
class MyProto:

    @guppy
    def foo(self: "MyProto", x: float) -> str: 
        return str(x)

MyProto.compile()