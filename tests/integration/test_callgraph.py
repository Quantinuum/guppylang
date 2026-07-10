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

    # After checking we should have call graph node for root, caller1, caller2 (but not
    # leaf since it doesn't call anything so it is only implicitly a node by being in
    # the list of callees for one of the callers).
    assert root.id in callgraph
    assert caller1.id in callgraph
    assert caller2.id in callgraph

    # Verify edges point to the right callees.
    assert caller1.id in callgraph[root.id]
    assert caller2.id in callgraph[root.id]
    assert leaf.id in callgraph[caller1.id]
    assert leaf.id in callgraph[caller2.id]


# TODO(callgraph): Should all functions be included in the graph? Does this lead to
# issues in the effects analysis or does it make it a bit quicker if not?
def test_no_call():
    """Test that functions with no calls are not included in the call graph."""

    @guppy
    def pure_function() -> int:
        return 100

    pure_function.check()

    assert pure_function.id not in ENGINE.call_graph


def test_recursive():
    """Test that recursive calls are recorded in the call graph."""

    @guppy
    def factorial(n: int) -> int:
        if n <= 1:
            return 1
        else:
            return n * factorial(n - 1)

    factorial.check()

    assert factorial.id in ENGINE.call_graph
    # Check that factorial calls itself.
    assert factorial.id in ENGINE.call_graph[factorial.id]


# TODO(callgraph): Figure out how to fix this test.
def test_nested_function():
    """Test that nested function calls are recorded in the call graph."""

    @guppy
    def outer() -> int:
        @guppy
        def inner() -> int:
            return 42

        return inner()

    outer.check()

    assert outer.id in ENGINE.call_graph
    # Check the outer function call exactly one function (the nested function).
    assert len(ENGINE.call_graph[outer.id]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
