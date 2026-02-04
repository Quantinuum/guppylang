from guppylang.std.debug import state_result
from guppylang.std.quantum import discard, qubit
from tests.util import compile_guppy

@compile_guppy
def main() -> None:
    q1 = qubit()
    state_result(q1)
    discard(q1)
