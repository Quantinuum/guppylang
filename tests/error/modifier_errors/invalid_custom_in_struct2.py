"""Ensuring that custom implementations are properly checked"""
from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import discard, qubit


@guppy.struct
class FooStruct:
    x: int

    @guppy.unitary
    class foo:
        n = guppy.nat_var("n")

        @guppy
        def __call__(self,q: qubit) -> None:
            pass

        @guppy
        def controlled(self, q: qubit, controls: array[int, n]) -> None:
            pass

        @guppy
        def daggered(self, q: qubit) -> None:
            pass
        

@guppy
def main() -> None:
    s = FooStruct(42)
    q = qubit()
    s.foo(q)
    discard(q)

main.compile()
