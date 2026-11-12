from guppylang import guppy
from guppylang.std.builtins import dagger, power
from guppylang.std.num import nat
from guppylang.std.quantum import h, measure, qubit


@guppy
def nested(q: qubit) -> None:
    with dagger:
        with power(nat(int(measure(qubit()).read()))):
            h(q)


nested.check()
