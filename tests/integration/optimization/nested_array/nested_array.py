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
from guppylang.std.quantum import cx, qubit


@guppy
def main(arr: array[array[qubit, 5], 3]) -> None:
    cx(arr[0][1], arr[0][2])
    cx(arr[0][1], arr[0][2])


# Output unoptimized Hugr so we can see the effect of optimization during test.
program = main.with_minimal_opt().compile_function()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
