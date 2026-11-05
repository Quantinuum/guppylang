from guppylang import guppy
from guppylang.std.builtins import control
from guppylang.std.quantum import measure, qubit


@guppy.struct
class S:
    q: qubit


@guppy
def allocate() -> S:
    return S(qubit())


@guppy
def main(c: qubit) -> None:
    with control(c):
        s = allocate()
        measure(s.q)


main.compile_function()
