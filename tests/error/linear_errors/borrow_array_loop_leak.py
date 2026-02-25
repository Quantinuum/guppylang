from guppylang import guppy, array, comptime
from guppylang.std.quantum import qubit, z


def build_phase_gadget_prog(n_qb: int):
    @guppy
    def phase_gadget() -> None:
        qs = array(qubit() for _ in range(comptime(n_qb)))
        # Allocated array of qubits is not consumed.

        for i in range(comptime(n_qb)):
            z(qs[i])

    return phase_gadget

phase_gadget_1 = build_phase_gadget_prog(5)
phase_gadget_1.check()