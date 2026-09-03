from guppylang.decorator import guppy
from guppylang.std.array import array
from guppylang.std.builtins import control, nat
from guppylang.std.quantum import measure, qubit


@guppy.unitary
class foo:
    n = guppy.nat_var("n")

    @guppy
    def __call__(q: qubit) -> None:
        pass

    @guppy
    def controlled(q: qubit, controls: array[qubit, n]) -> None:
        extra_control = qubit()
        helper(q, controls, extra_control)
        measure(extra_control)


@guppy
def helper[n: nat](
    q: qubit, controls: array[qubit, n], extra_control: qubit
) -> None:
    with control(controls), control(extra_control):
        foo(q)


@guppy
def main(q: qubit, control_qubit: qubit) -> None:
    with control(control_qubit):
        foo(q)


main.compile_function()
