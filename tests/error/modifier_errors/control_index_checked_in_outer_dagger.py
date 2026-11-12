from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.builtins import control, dagger
from guppylang.std.quantum import h, measure, qubit


@guppy
def nested(cs: array[qubit, 2], q: qubit) -> None:
    with dagger:
        with control(cs[int(measure(qubit()).read())]):
            h(q)


nested.check()
