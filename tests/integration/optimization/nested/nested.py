# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "guppylang==1.2.0",
#     "guppylang-internals==1.2.0",
# ]
# ///

from pathlib import Path
from sys import argv

from guppylang import guppy
from guppylang.std.builtins import array, owned, result
from guppylang.std.quantum import cz, h, measure, qubit


@guppy
def main() -> None:
    q1, q2, q3 = qubit(), qubit(), qubit()
    q1, q2, q3 = f(array(q1, q2, q3))
    b1 = measure(q1)
    b2 = measure(q2)
    b3 = measure(q3)

    result("b1", b1.read())
    result("b2", b2.read())
    result("b3", b3.read())


@guppy
def f(qs: array[qubit, 3] @ owned) -> array[qubit, 3]:
    for i in range(3):
        h(qs[i])
    for i in range(2):
        for j in range(3):
            cz(qs[j], qs[(j + 1) % 3])
    for i in range(3):
        h(qs[i])
    return qs


# Output unoptimized Hugr so we can see the effect of optimization during test.
program = main.with_minimal_opt().compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
