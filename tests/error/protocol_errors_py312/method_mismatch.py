from guppylang import guppy
from typing import Self

@guppy.protocol
class Addable[T]:
    @guppy.require
    def __add__(self, other: T) -> Self: ...

@guppy
def foo[T: Addable[int]](t: T) -> T:
    return t.__add__(42)

@guppy
def main() -> None:
    foo(0)
    foo(0.0)

main.compile()
