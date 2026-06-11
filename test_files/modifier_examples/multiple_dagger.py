"""An example with an even number of daggers, which should cancel out"""

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


@guppy(unitary=True)
def rotation(q: qubit) -> None:
    rx(q, angle(1 / 4))


@guppy
def main() -> None:
    t = qubit()

    with dagger:
        with dagger:
            rotation(t)

    with dagger, dagger, dagger:
        rotation(t)

    state_result("r", t)
    discard(t)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
