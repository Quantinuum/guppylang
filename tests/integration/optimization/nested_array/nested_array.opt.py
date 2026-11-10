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
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit


@guppy
def main(arr: array[array[qubit, 5], 3]) -> None:
    # it may be impossible to elide the three borrow/return pairs
    # of different indices in case these panic...so something like
    # def inner(ar: array[qubit, 5]) -> None:
    #    inner2(ar[1], ar[2])
    # def inner2(q1: qubit, q2: qubit) -> None:
    #    pass
    # inner(ar[0])
    pass


program = main.compile_function()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
