from guppylang.decorator import guppy

@guppy.protocol
class MyProto:
    id: int

    def foo(self: "MyProto", x: float) -> str: ...

MyProto.compile()