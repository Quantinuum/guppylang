import pytest
from hugr import ops as hops
from hugr import InPort
from hugr.std import PRELUDE

from guppylang import guppy
from guppylang_internals.engine import ENGINE
from guppylang.std.builtins import owned, panic
from guppylang.std.quantum import qubit
from guppylang.std.quantum.functional import cx, h

# ALAN TODO add test that a user-defined function calling a *declaration* gets the [ANY]

# ALAN TODO move hugr tests into test_side_effect_ordering.py,
# then move this file outside of integration


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

    data = ENGINE.call_graph.get((factorial.id, ()))
    assert data is not None
    # Check that factorial calls itself.
    assert (factorial.id, ()) in data


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
    assert len(data) == 1


def test_pure_quantum_calls_have_no_order_edges(validate):
    @guppy
    def apply_gates(q1: qubit @ owned, q2: qubit @ owned) -> tuple[qubit, qubit]:
        q1 = h(q1)
        q1, q2 = cx(q1, q2)
        return q1, q2

    @guppy
    def main(
        q1: qubit @ owned,
        q2: qubit @ owned,
        q3: qubit @ owned,
        q4: qubit @ owned,
    ) -> tuple[qubit, qubit, qubit, qubit]:
        q1, q2 = apply_gates(q1, q2)
        q3, q4 = apply_gates(q3, q4)
        q2, q3 = apply_gates(q2, q3)
        return q1, q2, q3, q4

    package = main.with_minimal_opt().compile_function()
    validate(package)

    hugr = package.modules[0]
    calls = [node for node, data in hugr.nodes() if isinstance(data.op, hops.Call)]
    assert len(calls) == 5

    [main_node] = [
        node
        for node, data in hugr.nodes()
        if isinstance(data.op, hops.FuncDefn) and "main" in data.op.f_name
    ]

    main_calls = [
        node
        for node, data in hugr.nodes()
        if isinstance(data.op, hops.Call) and main_node in ancestors(hugr, node)
    ]
    assert len(main_calls) == 3

    def has_directed_path(source, target):
        return any(
            destination.node == target or has_directed_path(destination.node, target)
            for _, destinations in hugr.outgoing_links(source)
            for destination in destinations
        )

    first_call, second_call, _ = main_calls
    assert not has_directed_path(first_call, second_call)
    assert not has_directed_path(second_call, first_call)


def ancestors(hugr, node):
    while (parent := hugr[node].parent) is not None:
        yield parent
        node = parent


def has_order_path(hugr, source, target):
    return any(
        node == target or has_order_path(hugr, node, target)
        for node in hugr.outgoing_order_links(source)
    )


def test_panicking_calls_have_order_edges(validate):
    @guppy
    def panicking_function() -> None:
        panic("From panicking function")

    @guppy
    def pure_function() -> None:
        pass

    @guppy
    def main() -> None:
        panicking_function()
        pure_function()
        panic("From main")
        pure_function()
        panicking_function()

    package = main.with_minimal_opt().compile_function()
    validate(package)

    hugr = package.modules[0]
    [main_node] = [
        node
        for node, data in hugr.nodes()
        if isinstance(data.op, hops.FuncDefn) and "main" in data.op.f_name
    ]

    main_calls = [
        node
        for node, data in hugr.nodes()
        if isinstance(data.op, hops.Call) and main_node in ancestors(hugr, node)
    ]

    def get_called_func_name(call_node):
        from hugr.tys import FunctionKind

        srcs = [
            srcs
            for tgt, srcs in hugr.incoming_links(call_node)
            if isinstance(hugr.port_kind(tgt), FunctionKind)
        ]
        [[static_outport]] = srcs
        op = hugr[static_outport.node].op
        assert isinstance(op, hops.FuncDefn)
        return op.f_name

    assert [
        "panicking_function" in get_called_func_name(node) for node in main_calls
    ] == [True, False, False, True]
    assert ["pure_function" in get_called_func_name(node) for node in main_calls] == [
        False,
        True,
        True,
        False,
    ]
    [panic_call1, pure_call1, pure_call2, panic_call2] = main_calls

    [panic_op] = [
        node
        for node, data in hugr.nodes()
        if isinstance(data.op, hops.ExtOp)
        and data.op.op_def().qualified_name()
        == PRELUDE.get_op("panic").qualified_name()
        and main_node in ancestors(hugr, node)
    ]

    assert has_order_path(hugr, panic_call1, panic_op)
    assert has_order_path(hugr, panic_op, panic_call2)
    for pure_call in [pure_call1, pure_call2]:
        for op in [panic_call1, panic_op, panic_call2]:
            assert not has_order_path(hugr, pure_call, op)
            assert not has_order_path(hugr, op, pure_call)


def test_nested_panicking_calls(validate):
    @guppy
    def main() -> None:
        def panicking_function() -> None:
            panic("From panicking function")

        def pure_function() -> None:
            pass

        panicking_function()
        pure_function()
        panic("From main")
        pure_function()
        panicking_function()

    package = main.with_minimal_opt().compile_function()
    validate(package)

    hugr = package.modules[0]
    [main_node] = [
        node
        for node, data in hugr.nodes()
        if isinstance(data.op, hops.FuncDefn) and "main" in data.op.f_name
    ]

    main_calls = [
        node
        for node, data in hugr.nodes()
        if isinstance(data.op, hops.CallIndirect) and main_node in ancestors(hugr, node)
    ]

    def get_called_func_name(call_indirect):
        [loadfunc] = hugr.linked_ports(InPort(call_indirect, 0))
        assert isinstance(hugr[loadfunc.node].op, hops.LoadFunc)
        [func] = hugr.linked_ports(InPort(loadfunc.node, 0))
        assert isinstance(hugr[func.node].op, hops.FuncDefn)
        return hugr[func.node].op.f_name

    assert [
        "panicking_function" in get_called_func_name(node) for node in main_calls
    ] == [True, False, False, True]
    assert ["pure_function" in get_called_func_name(node) for node in main_calls] == [
        False,
        True,
        True,
        False,
    ]
    [panic_call1, pure_call1, pure_call2, panic_call2] = main_calls

    [panic_op] = [
        node
        for node, data in hugr.nodes()
        if isinstance(data.op, hops.ExtOp)
        and data.op.op_def().qualified_name()
        == PRELUDE.get_op("panic").qualified_name()
        and main_node in ancestors(hugr, node)
    ]

    assert has_order_path(hugr, panic_call1, panic_op)
    assert has_order_path(hugr, panic_op, panic_call2)

    # These order paths would lead to cycles:
    assert not has_order_path(hugr, pure_call1, panic_call1)
    for op in [panic_op, pure_call2, panic_call2]:
        assert not has_order_path(hugr, op, pure_call1)
    assert not has_order_path(hugr, panic_call2, pure_call2)
    for op in [panic_call1, pure_call1, panic_op]:
        assert not has_order_path(hugr, pure_call2, op)

    # For the time being:
    if (
        has_order_path(hugr, panic_call1, pure_call1)
        and all(
            has_order_path(hugr, pure_call1, op)
            for op in [panic_op, pure_call2, panic_call2]
        )
        and all(
            has_order_path(hugr, op, pure_call2)
            for op in [panic_call1, pure_call1, panic_op]
        )
        and has_order_path(hugr, pure_call2, panic_call2)
    ):
        pytest.xfail(
            "Calls to nested functions are not resolved in checking,"
            " leading to spurious order edges"
        )

    # Otherwise - the desired outcome when previous is fixed:
    for pure_call in [pure_call1, pure_call2]:
        for op in [panic_call1, panic_op, panic_call2]:
            assert not has_order_path(hugr, pure_call, op)
            assert not has_order_path(hugr, op, pure_call)
