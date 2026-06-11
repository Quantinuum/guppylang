"""A stress test for nested control and dagger modifiers."""

from pathlib import Path
from sys import argv

from guppylang import guppy
from guppylang.std.builtins import control, dagger
from guppylang.std.debug import state_result
from guppylang.std.quantum import angle, discard, qubit, rx, h


from guppylang.experimental import enable_experimental_features

enable_experimental_features()


@guppy
def main() -> None:
    c = qubit()
    q = qubit()
    h(c)
    with dagger:
        with control(c):
            with dagger:
                rx(q, angle(1 / 3))

    state_result("r", c, q)

    discard(q)
    discard(c)


program = main.compile()
Path(argv[0]).with_suffix(".hugr").write_bytes(program.to_bytes())
