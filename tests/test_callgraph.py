from guppylang import guppy
from guppylang_internals.engine import ENGINE


def test_simple():
    """Test that a simple call graph is built correctly."""

    @guppy.declare
    def leaf_decl() -> int: ...

    @guppy
    def leaf() -> int:
        return 42

    @guppy
    def caller1() -> int:
        return leaf() + leaf_decl()

    @guppy
    def caller2() -> int:
        return leaf() + leaf_decl()

    @guppy
    def root() -> int:
        return caller1() + caller2()

    root.check()

    # After checking we should have call graph nodes for root, caller1, caller2 and leaf
    # (leaf since it doesn't call anything so it is only implicitly a node by being in
    # the list of callees for one of the callers).
    root_data = ENGINE.call_graph.get((root.id, ()))
    assert root_data is not None
    caller1_data = ENGINE.call_graph.get((caller1.id, ()))
    assert caller1_data is not None
    caller2_data = ENGINE.call_graph.get((caller2.id, ()))
    assert caller2_data is not None
    assert (leaf.id, ()) in ENGINE.call_graph
    assert ENGINE.call_graph.get((leaf_decl.id, ())) is None

    # Verify edges point to the right callees.
    assert (caller1.id, ()) in root_data
    assert (caller2.id, ()) in root_data
    assert (leaf.id, ()) in caller1_data
    assert (leaf_decl.id, ()) in caller1_data
    assert (leaf.id, ()) in caller2_data
    assert (leaf_decl.id, ()) in caller2_data


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
