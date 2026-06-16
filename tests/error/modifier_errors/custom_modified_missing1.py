
from guppylang.decorator import guppy
from guppylang.std.quantum import h, x, measure, qubit
import guppylang
guppylang.enable_experimental_features()

@guppy.unitary
class foo:
    @guppy
    def __call__(q: qubit) -> None:
        h(q)
        c = qubit()
        measure(c)

    @guppy
    def call_daggered(q: qubit) -> None:
        x(q)


@guppy(controllable=True)
def main(q: qubit) -> None:
    foo(q)
    
main.check()

