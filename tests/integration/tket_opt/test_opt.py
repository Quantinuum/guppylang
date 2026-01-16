from guppylang import guppy
from guppylang.std.angles import pi
from guppylang.std.quantum import qubit, cx, h, s, t, rz
from guppylang.std.builtins import array

from pytket.passes import RemoveRedundancies, CliffordSimp, SquashRzPhasedX

from tket.passes import NormalizeGuppy, PytketHugrPass, PassResult

from hugr.hugr.base import Hugr


def _count_ops(hugr: Hugr, string_name: str) -> int:
    count = 0
    for _, data in hugr.nodes():
        if string_name in data.op.name():
            count += 1

    return count


normalize = NormalizeGuppy()


# NormalizeGuppy documentation
# -> https://quantinuum.github.io/tket2/generated/tket.passes.NormalizeGuppy.html#tket.passes.NormalizeGuppy
def test_guppy_normalization() -> None:
    @guppy
    def pauli_zz_rotation(q0: qubit, q1: qubit) -> None:
        cx(q0, q1)
        t(q1)
        cx(q0, q1)

        unnormalized_hugr: Hugr = pauli_zz_rotation.compile_function().modules[0]

        # Count ops prior to normalization
        assert _count_ops(unnormalized_hugr, "DataflowBlock") == 1
        assert _count_ops(unnormalized_hugr, "MakeTuple") == 3

        normalized_hugr = normalize(unnormalized_hugr)

        # Test that the dataflow block is inlined by NormalizeGuppy
        assert _count_ops(normalized_hugr, "DataflowBlock") == 0
        # Test that MakeTuple nodes are removed by NormalizeGuppy
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


def test_redundant_cx_cancellation_with_arrays():
    @guppy
    def arr_cx(arr: array[qubit, 2]) -> None:
        h(arr[0])
        cx(arr[0], arr[1])
        cx(arr[0], arr[1])

    hugr_graph: Hugr = normalize(arr_cx.compile_function().modules[0])
    opt_pass = PytketHugrPass(RemoveRedundancies())
    new_hugr = opt_pass(hugr_graph)
    assert _count_ops(new_hugr, "CX") == 0


def test_clifford_simplification() -> None:
    @guppy
    def simple_clifford(q0: qubit, q1: qubit) -> None:
        cx(q0, q1)
        s(q1)
        cx(q1, q0)
        my_hugr_graph = normalize(simple_clifford.compile_function().modules[0])
        cliff_pass = PytketHugrPass(CliffordSimp(allow_swaps=True))
        opt_hugr = cliff_pass(my_hugr_graph)
        # test that we can cancel a CX gate by using an implicit swap
        assert _count_ops(opt_hugr, "CX") == 1


def test_1q_rz_squashing() -> None:
    @guppy
    def redundant_1q_gates(q0: qubit) -> None:
        rz(q0, pi / 2)
        rz(q0, pi / 2)
        rz(q0, pi / 2)

    hugr_graph: Hugr = normalize(redundant_1q_gates.compile_function().modules[0])
    opt_pass = PytketHugrPass(SquashRzPhasedX())
    new_hugr = opt_pass(hugr_graph)
    assert _count_ops(new_hugr, "Rz") == 1
