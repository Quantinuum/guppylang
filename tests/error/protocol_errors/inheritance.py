from guppylang.decorator import guppy

class OtherClass:
    pass

@guppy.protocol
class MyProto(OtherClass):
    def foo(self: "MyProto", x: int) -> str: ...


MyProto.compile()
