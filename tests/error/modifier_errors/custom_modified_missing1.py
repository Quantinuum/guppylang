
from guppylang.decorator import guppy
from guppylang.std.quantum import h, x, measure, qubit


@guppy.unitary
class foo:
    @guppy
    def __call__(q: qubit) -> None:
        h(q)
        c = qubit()
        measure(c)

    @guppy
    def daggered(q: qubit) -> None:
        x(q)


@guppy(controllable=True)
def main(q: qubit) -> None:
    foo(q)
    
main.check()

