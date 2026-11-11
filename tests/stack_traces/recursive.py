from guppylang import guppy
from guppylang.std.quantum import cx, discard, qubit


@guppy
def recursive_allocate(source: qubit) -> None:
    q = qubit()
    cx(source, q)
    recursive_allocate(q)
    discard(q)


@guppy
def main() -> None:
    q = qubit()
    recursive_allocate(q)
    discard(q)


main.with_minimal_opt().emulator(n_qubits=4, debug_mode=True).run()
