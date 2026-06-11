"""Test the use of a classical function inside modifiers"""

from pathlib import Path
from sys import argv
import sys

from guppylang import guppy
from guppylang.std.builtins import dagger
from guppylang.std.debug import state_result
from guppylang.std.quantum import discard, qubit, angle
from guppylang.std.quantum import rx

sys.path.append(str(Path(__file__).resolve().parents[1]))

from guppylang.experimental import enable_experimental_features

enable_experimental_features()


@guppy
def fuu(i: int) -> int:
    return i + 1


@guppy
def main() -> None:
    q = qubit()
    with dagger:
        rx(q, angle(1 / fuu(2)))

    state_result("r", q)
    discard(q)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
