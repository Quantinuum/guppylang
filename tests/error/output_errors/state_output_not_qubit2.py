from guppylang.std.debug import state_output
from guppylang.std.quantum import discard, qubit
from tests.util import compile_guppy

@compile_guppy
def main() -> None:
    q1 = qubit()
    state_output("tag", q1, 123)
    discard(q1)
