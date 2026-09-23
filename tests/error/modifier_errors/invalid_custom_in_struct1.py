"""Checking that when a custom unitary is defined as a struct method, the custom methods signature is properly tested"""
from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import discard, qubit

n = guppy.nat_var("n")

@guppy.struct
class FooStruct:
    x: int

    @guppy.unitary
    class foo:

        @guppy
        def __call__(self, q: qubit) -> None:
            pass

        @guppy
        def controlled(self, q: qubit, controls: array[int, n]) -> None:
            pass

@guppy
def main() -> None:
    s = FooStruct(42)
    q = qubit()
    s.foo(q)
    discard(q)

main.compile()
