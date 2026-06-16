
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

    @guppy
    def call_controlled[c: nat](q: qubit, _controls: array[qubit, c]) -> None:
        cx(_controls[0], q)

@guppy
def main(q: qubit) -> None:
    with dagger:
        foo(q)

main.check()

