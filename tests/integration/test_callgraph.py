import pytest
from hugr import ops as hops

from guppylang import guppy
from guppylang_internals.engine import ENGINE
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit
from guppylang.std.quantum.functional import cx, h


def test_simple():
    """Test that a simple call graph is built correctly."""

    @guppy
    def leaf() -> int:
        return 42

    @guppy
    def caller1() -> int:
        return leaf()

    @guppy
    def caller2() -> int:
        return leaf()

    @guppy
    def root() -> int:
        return caller1() + caller2()

    root.check()

    callgraph = ENGINE.call_graph

    # After checking we should have call graph node for root, caller1, caller2 (but not
    # leaf since it doesn't call anything so it is only implicitly a node by being in
    # the list of callees for one of the callers).
    root_data = ENGINE.call_graph.get((root.id, ()))
    assert root_data is not None
    caller1_data = ENGINE.call_graph.get((caller1.id, ()))
    assert caller1_data is not None
    caller2_data = ENGINE.call_graph.get((caller2.id, ()))
    assert caller2_data is not None

    # Verify edges point to the right callees.
    assert (caller1.id, ()) in root_data.callee_defs
    assert (caller2.id, ()) in root_data.callee_defs
    assert (leaf.id, ()) in caller1_data.callee_defs
    assert (leaf.id, ()) in caller2_data.callee_defs


def test_recursive():
    """Test that recursive calls are recorded in the call graph."""

    @guppy
    def factorial(n: int) -> int:
        if n <= 1:
            return 1
        else:
            return n * factorial(n - 1)

    factorial.check()

    data = ENGINE.call_graph.get((factorial.id, ()))
    assert data is not None
    # Check that factorial calls itself.
    assert (factorial.id, ()) in data.callee_defs


@pytest.mark.xfail(
    match="0 == 1",
    reason="Nested functions are resolved as indirect calls to unknown target",
)
def test_nested_function():
    """Test that nested function calls are recorded in the call graph."""

    @guppy
    def outer() -> int:
        @guppy
        def inner() -> int:
            return 42

        return inner()

    outer.check()

    data = ENGINE.call_graph.get((outer.id, ()))
    assert data is not None
    # Check the outer function call exactly one function (the nested function).
    assert len(data.callee_defs) == 1


def test_pure_quantum_calls_have_no_order_edges(validate):
    @guppy
    def apply_gates(q1: qubit @ owned, q2: qubit @ owned) -> tuple[qubit, qubit]:
        q1 = h(q1)
        q1, q2 = cx(q1, q2)
        return q1, q2

    @guppy
    def main(q1: qubit @ owned, q2: qubit @ owned) -> tuple[qubit, qubit]:
        q1, q2 = apply_gates(q1, q2)
        return apply_gates(q1, q2)

    package = main.with_minimal_opt().compile_function()
    validate(package)

    hugr = package.modules[0]
    calls = [node for node, data in hugr.nodes() if isinstance(data.op, hops.Call)]
    assert len(calls) == 4
    for call in calls:
        assert not list(hugr.incoming_order_links(call))
        assert not list(hugr.outgoing_order_links(call))
