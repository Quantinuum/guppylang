from guppylang.std.debug import state_result
from guppylang.std.quantum import discard, qubit
from tests.util import compile_guppy

@compile_guppy
def main(y: bool) -> None:
    q1 = qubit()
    state_result("foo" if y else "bar", q1)
    discard(q1)
