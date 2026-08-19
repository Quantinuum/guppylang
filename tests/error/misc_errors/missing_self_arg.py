from guppylang import guppy
from guppylang.std.builtins import nat, qubit, array
from guppylang.std.quantum import discard_array

@guppy.struct(frozen=True)
class StatePrep[N: nat]:
    @guppy
    def prep() -> array[qubit, N]:
        return array(qubit() for _ in range(N))


@guppy
def main() -> None:
    sp = StatePrep[3]()
    discard_array(sp.prep())


main.compile()