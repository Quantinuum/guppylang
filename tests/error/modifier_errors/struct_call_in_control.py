from guppylang import guppy
from guppylang.std.builtins import control
from guppylang.std.quantum import h, measure, qubit


@guppy.struct
class S:
    q: qubit


@guppy
def use(s: S) -> None:
    q = qubit()
    h(s.q)
    measure(q)


@guppy
def main(c: qubit, s: S) -> None:
    with control(c):
        use(s)


main.with_minimal_opt().compile_function()
