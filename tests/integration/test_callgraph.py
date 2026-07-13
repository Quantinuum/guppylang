import pytest
from guppylang import guppy
from guppylang_internals.engine import ENGINE


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

    # After checking we should have call graph node for root, caller1, caller2, leaf
    root = (root.id, ())
    assert root in callgraph
    caller1 = (caller1.id, ())
    assert caller1 in callgraph
    caller2 = (caller2.id, ())
    assert caller2 in callgraph
    leaf = (leaf.id, ())
    assert leaf in callgraph

    # Verify edges point to the right callees.
    assert callgraph.has_edge(root, caller1)
    assert callgraph.has_edge(root, caller2)
    assert callgraph.has_edge(caller1, leaf)
    assert callgraph.has_edge(caller2, leaf)


def test_recursive():
    """Test that recursive calls are recorded in the call graph."""

    @guppy
    def factorial(n: int) -> int:
        if n <= 1:
            return 1
        else:
            return n * factorial(n - 1)

    factorial.check()

    assert (factorial.id, ()) in ENGINE.call_graph
    # Check that factorial calls itself.
    assert ENGINE.call_graph.has_edge((factorial.id, ()), (factorial.id, ()))


@pytest.mark.xfail(
    match="0 == 1",
    reason="Nested functions are resolved as indirect calls to unknown target"
    "Believed because of https://github.com/Quantinuum/guppylang/issues/2038",
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
