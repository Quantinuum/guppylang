import pytest
from guppylang import guppy
from guppylang_internals.checker.callgraph import CallGraph, is_concrete
from guppylang_internals.definition.common import DefId
from guppylang_internals.engine import ENGINE
from guppylang_internals.tys.arg import ConstArg
from guppylang_internals.tys.builtin import nat_type
from guppylang_internals.tys.const import BoundConstVar, ConstValue


def test_is_concrete():
    def_id = DefId.fresh()

    assert is_concrete((def_id, (ConstArg(ConstValue(nat_type(), 1)),)))
    assert not is_concrete((def_id, (ConstArg(BoundConstVar(nat_type(), "n", 0)),)))


def test_condensed_topological_and_external_callees():
    a = (DefId.fresh(), ())
    b = (DefId.fresh(), ())
    c = (DefId.fresh(), ())
    d = (DefId.fresh(), ())
    external = (DefId.fresh(), ())
    callgraph = CallGraph(
        {
            a: [b],
            b: [c, external],
            c: [b, d],
            d: [],
        }
    )

    component_a, component_bc, component_d = callgraph.condensed
    assert component_a.members == frozenset({a})
    assert component_bc.members == frozenset({b, c})
    assert component_d.members == frozenset({d})
    assert component_a.external_callees == frozenset({(a, component_bc, b)})
    assert component_bc.external_callees == frozenset(
        {
            (b, None, external),
            (c, component_d, d),
        }
    )
    assert not component_d.external_callees


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
    assert (caller1.id, ()) in root_data
    assert (caller2.id, ()) in root_data
    assert (leaf.id, ()) in caller1_data
    assert (leaf.id, ()) in caller2_data


def test_recursive():
    """Test that recursive calls are recorded in the call graph."""

    @guppy
    def factorial(n: int) -> int:
        if n <= 1:
            return 1
        else:
            return n * factorial(n - 1)

    factorial.check()

    mono_id = (factorial.id, ())
    assert mono_id in ENGINE.call_graph[mono_id]  # factorial calls itself


@pytest.mark.xfail(
    match="0 == 1",
    reason="Nested functions are resolved as indirect calls to unknown target"
    " (see https://github.com/Quantinuum/guppylang/issues/2272)",
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
    # Check the outer function calls exactly one function (the nested function).
    assert len(data) == 1
