
from guppylang.decorator import guppy
from guppylang.std.num import nat
from guppylang.std.quantum import array, cx, h, measure, qubit
from guppylang.std.builtins import dagger
import guppylang
guppylang.enable_experimental_features()

@guppy.unitary
class foo:
    @guppy
    def __call__(q: qubit) -> None:
        h(q)
        c = qubit()
        measure(c)


@guppy(unitary=True)
def main(q: qubit) -> None:
    foo(q)

main.check()

