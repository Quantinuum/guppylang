from typing import Protocol
from guppylang.decorator import guppy


@guppy.struct
class MyProto(Protocol):

    @guppy.declare
    def foo(self: "MyProto", x: int) -> str: ...

MyProto.compile()