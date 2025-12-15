from guppylang import guppy
from guppylang.std.quantum import qubit, cx, h, s, t

from pytket.passes import RemoveRedundancies, CliffordSimp

from tket.passes import NormalizeGuppy, PytketHugrPass, PassResult

from hugr.hugr.base import Hugr


def _count_ops(hugr: Hugr, string_name: str) -> int:
    count = 0
    for _, data in hugr.nodes():
        if string_name in data.op.name():
            count += 1

    return count


normalize = NormalizeGuppy()


def test_guppy_normalization() -> None:
    @guppy
    def pauli_zz_rotation(q0: qubit, q1: qubit) -> None:
        cx(q0, q1)
        t(q1)
        cx(q0, q1)

        normalized_hugr: Hugr = normalize(
            pauli_zz_rotation.compile_function().modules[0]
        )

        assert _count_ops(normalized_hugr, "DataflowBlock") == 0
        assert _count_ops(normalized_hugr, "MakeTuple") == 0


def test_redundant_cx_cancellation() -> None:
    @guppy
    def redundant_cx(q0: qubit, q1: qubit) -> None:
        h(q0)
        # Two adjacent CX gates with the same control and target can be cancelled.
        cx(q0, q1)
        cx(q0, q1)

    my_hugr_graph = normalize(redundant_cx.compile_function().modules[0])
    rr_pass = PytketHugrPass(RemoveRedundancies())
    pass_result: PassResult = rr_pass.run(my_hugr_graph)
    assert pass_result.modified
    assert _count_ops(pass_result.hugr, "CX") == 0
    assert _count_ops(pass_result.hugr, "H") == 1


def test_clifford_simplification() -> None:
    @guppy
    def simple_clifford(q0: qubit, q1: qubit) -> None:
        cx(q0, q1)
        s(q1)
        cx(q1, q0)
        my_hugr_graph = normalize(simple_clifford.compile_function().modules[0])
        cliff_pass = PytketHugrPass(CliffordSimp(allow_swaps=True))
        opt_hugr = cliff_pass(my_hugr_graph)
        assert _count_ops(opt_hugr, "CX") == 1
