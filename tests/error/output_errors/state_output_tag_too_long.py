from guppylang.std.builtins import comptime
from guppylang.std.debug import state_output
from guppylang.std.quantum import discard, qubit
from tests.util import compile_guppy

TAG_MAX_LEN = 200

@compile_guppy
def main() -> None:
    q1 = qubit()
    state_output(comptime("a" * (TAG_MAX_LEN + 1)), q1)
    discard(q1)
