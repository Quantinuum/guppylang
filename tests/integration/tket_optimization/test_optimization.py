from guppylang import guppy
from guppylang.std.quantum import qubit, cx, h

from pytket.passes import RemoveRedundancies

from tket.passes import NormalizeGuppy, PytketHugrPass, PassResult

from hugr.hugr.base import Hugr


def _count_ops(hugr: Hugr, string_name: str) -> int:
    count = 0
    for _, data in hugr.nodes():
        if string_name in data.op.name():
            count += 1

    return count


normalize = NormalizeGuppy()


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
