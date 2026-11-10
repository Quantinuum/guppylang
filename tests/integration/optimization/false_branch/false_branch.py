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
from guppylang.std.builtins import result
from guppylang.std.quantum import h, measure, qubit


@guppy
def main() -> None:
    q = qubit()
    h(q)
    if True:
        h(q)
    if False:
        h(q)
    b = measure(q).read()

    result("b", b)


# Output unoptimized Hugr so we can see the effect of optimization during test.
program = main.with_minimal_opt().compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
