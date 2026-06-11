"""Testing a dagger modifier on multiple gates"""

from pathlib import Path
from sys import argv
import sys

from guppylang import guppy
from guppylang.std.builtins import dagger
from guppylang.std.debug import state_result
from guppylang.std.quantum import discard, qubit
from guppylang.std.quantum import sdg, h

sys.path.append(str(Path(__file__).resolve().parents[1]))

from guppylang.experimental import enable_experimental_features

enable_experimental_features()


@guppy
def main() -> None:
    t = qubit()

    with dagger:
        h(t)
        sdg(t)
        h(t)

    state_result("r", t)
    discard(t)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
