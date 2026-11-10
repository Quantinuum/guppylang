# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "guppylang==1.1.4",
#     "guppylang-internals==1.1.4",
# ]
# ///

"""Some angle logic that reduces to the identity.

This may be harder to optimize, as it requires const-folding angles through loop
unpeeling.
"""

from pathlib import Path
from sys import argv

from guppylang import guppy
from guppylang.std.angles import angle
from guppylang.std.builtins import owned, result
from guppylang.std.quantum import h, measure, qubit, rz


@guppy
def main() -> None:
    q = qubit()
    q = f(q)
    b = measure(q)

    result("b", b.read())


@guppy
def g(q: qubit, x: angle) -> None:
    rz(q, x / 2 - angle(0.1))
    rz(q, x / 2 + angle(0.1))


@guppy
def f(q: qubit @ owned) -> qubit:
    h(q)
    x: angle = angle(0.0)
    for i in range(5):
        g(q, x)
        x += angle(0.2)
    h(q)
    return q


# Output unoptimized Hugr so we can see the effect of optimization during test.
program = main.with_minimal_opt().compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
