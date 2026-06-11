"""Testing classical array operations in modifiers"""

from pathlib import Path
from sys import argv
import sys

from guppylang import guppy
from guppylang.std.debug import state_result
from guppylang.std.quantum import discard, qubit, h, x
from guppylang.std.builtins import array
import guppylang
from guppylang.std.builtins import control, dagger

sys.path.append(str(Path(__file__).resolve().parents[1]))


guppylang.enable_experimental_features()


@guppy
def main() -> None:
    arr = array(1, 1, 1, 1, 1)
    q = qubit()
    x(q)
    with control(q), dagger:
        arr[0] += 1
        arr[0] *= 2

    if arr[0] == 4:
        h(q)

    state_result("r", q)
    discard(q)


program = main.compile_function()
program_bytes = program.to_bytes()
Path(argv[0]).with_suffix(".hugr").write_bytes(program_bytes)
