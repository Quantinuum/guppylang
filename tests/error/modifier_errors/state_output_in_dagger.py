from guppylang import guppy, qubit
from guppylang.std.builtins import dagger
from guppylang.std.debug import state_output
from guppylang.std.quantum import measure



@guppy
def test() -> None:
    q = qubit()
    with dagger():
        state_output("a", q)
    measure(q)

test.compile()
