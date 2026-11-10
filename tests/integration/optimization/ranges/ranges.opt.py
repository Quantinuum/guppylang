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
from guppylang.std.quantum import measure, qubit


@guppy
def main() -> None:
    q1, q2, q3, q4 = qubit(), qubit(), qubit(), qubit()
    b1 = measure(q1)
    b2 = measure(q2)
    b3 = measure(q3)
    b4 = measure(q4)

    result("b1", b1.read())
    result("b2", b2.read())
    result("b3", b3.read())
    result("b4", b4.read())


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
