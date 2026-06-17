from guppylang.decorator import guppy

class OtherClass:
    pass

@guppy.protocol
class MyProto(OtherClass):
    @guppy.require
    def foo(self: "MyProto", x: int) -> str: ...


MyProto.compile()
