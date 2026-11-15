from guppylang import guppy
from guppylang.std.builtins import power
from guppylang.std.num import nat
from guppylang.std.quantum import h, qubit


@guppy.declare
def exponent() -> nat: ...


@guppy(unitary=True)
def main(q: qubit) -> None:
    with power(exponent()):
        h(q)


main.check()
