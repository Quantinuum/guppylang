"""Tests that the compiler correctly inserts order edges between operations that have
side-effects.
"""

import pytest
from hugr import ops, Hugr, Node
from hugr.std import PRELUDE
from hugr import ops as hops
from hugr import InPort

from guppylang import guppy
from guppylang.std.builtins import owned, panic
from guppylang.std.quantum import qubit
from guppylang.std.quantum.functional import cx, h

from guppylang_internals.std._internal.compiler.tket_exts import (
    QUANTUM_EXTENSION,
    QSYSTEM_RANDOM_EXTENSION,
    RESULT_EXTENSION,
)
from guppylang.std.builtins import output, array
from guppylang.std.qsystem.random import RNG
from guppylang.std.quantum import discard, measure


def find_ext_nodes(hugr: Hugr, qualified_name: str) -> list[Node]:
    """Returns all extension nodes in a Hugr that match the given qualified name."""
    return [
        node for node, data in hugr.nodes() if name_matches(data.op, qualified_name)
    ]


def name_matches(op: ops.Op, qualified_name: str) -> bool:
    """Checks if an op is an extension op that matches the given qualified name."""
    match op:
        case ops.ExtOp() as ext_op:
            return ext_op.op_def().qualified_name() == qualified_name
        case ops.Custom(op_name=op_name, extension=extension):
            return qualified_name == (
                f"{extension}.{op_name}" if extension else op_name
            )
        case _:
            return False


def check_order(hugr: Hugr, nodes: list[Node]) -> None:
    """Checks that the provided nodes appear in the specified order in the order-edge
    graph."""
    # Do a DFS traversal of the order edge graph starting at the first node
    stack = [nodes[0]]
    visited = set()
    while stack:
        curr = stack.pop()
        visited.add(curr)
        if curr in nodes:
            # Check this node is the next one in the sequence
            assert curr == nodes.pop(0)
            stack.clear()  # Only follow the order edges from this node
        for n in hugr.outgoing_order_links(curr):
            assert n not in visited, "Order edge graph must be acyclic"
            stack.append(n)
    # Check that all specified nodes occurred in the graph
    assert len(nodes) == 0


def test_input_output(validate):
    @guppy
    def main() -> None:
        q = qubit()
        q = f(q)
        b = measure(q).read()

        output("b", b)

    @guppy
    def f(q: qubit @ owned) -> qubit:
        return q

    program = main.compile()
    validate(program)

    hugr = program.modules[0]
    [r] = find_ext_nodes(hugr, RESULT_EXTENSION.get_op("result_bool").qualified_name())
    [inp, out] = hugr.children(hugr[r].parent)[:2]
    check_order(hugr, [inp, r, out])


def test_output_panic(validate):
    @guppy
    def test() -> None:
        output("a", True)
        output("b", 10)
        panic("Boo!")
        exit("Foo!", 1)
        output("c", 10.5)

    compiled = test.compile_function()
    validate(compiled)

    # Check that we have the expected order edges between the outputs
    hugr = compiled.modules[0]
    [a] = find_ext_nodes(hugr, RESULT_EXTENSION.get_op("result_bool").qualified_name())
    [b] = find_ext_nodes(hugr, RESULT_EXTENSION.get_op("result_int").qualified_name())
    [p] = find_ext_nodes(hugr, PRELUDE.get_op("panic").qualified_name())
    [e] = find_ext_nodes(hugr, PRELUDE.get_op("exit").qualified_name())
    [c] = find_ext_nodes(hugr, RESULT_EXTENSION.get_op("result_f64").qualified_name())
    check_order(hugr, [a, b, p, e, c])


def test_qalloc_qfree(validate):
    @guppy
    def test() -> None:
        q1 = qubit()
        discard(q1)
        q2 = qubit()
        measure(q2)

    compiled = test.compile_function()
    validate(compiled)

    # Check that we have the expected order edges between the allocations and frees
    hugr = compiled.modules[0]
    [a1, a2] = find_ext_nodes(hugr, QUANTUM_EXTENSION.get_op("QAlloc").qualified_name())
    [d1] = find_ext_nodes(hugr, QUANTUM_EXTENSION.get_op("QFree").qualified_name())
    [d2] = find_ext_nodes(
        hugr, QUANTUM_EXTENSION.get_op("MeasureFree").qualified_name()
    )
    check_order(hugr, [a1, d1, a2, d2])


def test_rng_context_lifetimes(validate):
    @guppy
    def test() -> None:
        rng = RNG(42)
        _ = rng.random_int()
        rng.discard()

        rng = RNG(84)
        _ = rng.random_int()
        rng.discard()

    compiled = test.compile_function()
    validate(compiled)

    hugr = compiled.modules[0]
    [new1, new2] = find_ext_nodes(
        hugr, QSYSTEM_RANDOM_EXTENSION.get_op("NewRNGContext").qualified_name()
    )
    [delete1, delete2] = find_ext_nodes(
        hugr, QSYSTEM_RANDOM_EXTENSION.get_op("DeleteRNGContext").qualified_name()
    )
    [inp, out] = hugr.children(hugr[new1].parent)[:2]
    check_order(hugr, [inp, new1, delete1, new2, delete2, out])


def test_rng_effect_propagates_through_call(validate):
    @guppy
    def use_rng() -> None:
        rng = RNG(42)
        _ = rng.random_int()
        rng.discard()

    @guppy
    def test() -> None:
        q1 = qubit()
        discard(q1)
        use_rng()
        q2 = qubit()
        discard(q2)

    compiled = test.with_minimal_opt().compile_function()
    validate(compiled)

    hugr = compiled.modules[0]
    [delete] = find_ext_nodes(
        hugr, QSYSTEM_RANDOM_EXTENSION.get_op("DeleteRNGContext").qualified_name()
    )
    helper_parent = hugr[delete].parent
    [constructor_call] = [
        node
        for node, data in hugr.nodes()
        if isinstance(data.op, ops.Call) and data.parent == helper_parent
    ]
    [helper_inp, helper_out] = hugr.children(helper_parent)[:2]
    check_order(hugr, [helper_inp, constructor_call, delete, helper_out])

    [alloc1, alloc2] = find_ext_nodes(
        hugr, QUANTUM_EXTENSION.get_op("QAlloc").qualified_name()
    )
    [free1, free2] = find_ext_nodes(
        hugr, QUANTUM_EXTENSION.get_op("QFree").qualified_name()
    )
    [call] = [
        node
        for node, data in hugr.nodes()
        if isinstance(data.op, ops.Call) and data.parent == hugr[alloc1].parent
    ]
    check_order(hugr, [alloc1, free1, call, alloc2, free2])


def test_call(validate):
    @guppy
    def my_discard(q: qubit @ owned) -> None:
        discard(q)

    @guppy
    def test() -> None:
        q1 = qubit()
        my_discard(q1)
        q2 = qubit()
        f = my_discard
        f(q2)

    # Disable optimization so the calls don't get inlined.
    compiled = test.with_minimal_opt().compile_function()
    validate(compiled)

    # Check that we have the expected order edges between the allocations and calls
    hugr = compiled.modules[0]
    [a1, a2] = find_ext_nodes(hugr, QUANTUM_EXTENSION.get_op("QAlloc").qualified_name())
    [d1, d2] = [node for node, data in hugr.nodes() if isinstance(data.op, ops.Call)]
    check_order(hugr, [a1, d1, a2, d2])


def test_nested(validate):
    @guppy
    def test() -> None:
        qs1 = array(qubit() for _ in range(10))
        array(measure(q).read() for q in qs1)
        qs2 = array(qubit() for _ in range(10))
        array(discard(q) for q in qs2)

    compiled = test.compile_function()
    validate(compiled)

    # Check that we have the expected order edges between the comprehension tail loops
    hugr = compiled.modules[0]
    [l1, l2, l3, l4] = [
        node for node, data in hugr.nodes() if isinstance(data.op, ops.TailLoop)
    ]
    [inp, out] = hugr.children(hugr[l1].parent)[:2]
    check_order(hugr, [inp, l1, l2, l3, l4, out])

    for loop in [l1, l2, l3, l4]:
        check_order(hugr, hugr.children(loop)[:2])


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


def get_called_func_name(hugr, call_node):
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


def test_panicking_calls_have_order_edges(validate):
    @guppy
    def panicking_func() -> None:
        panic("From panicking function")

    @guppy
    def pure_func() -> None:
        pass

    @guppy
    def main() -> None:
        panicking_func()
        pure_func()
        panic("From main")
        pure_func()
        panicking_func()

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

    assert [
        "panicking_func" in get_called_func_name(hugr, node) for node in main_calls
    ] == [True, False, False, True]
    assert ["pure_func" in get_called_func_name(hugr, node) for node in main_calls] == [
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

    check_order(hugr, [panic_call1, panic_op, panic_call2])

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

    check_order(hugr, [panic_call1, panic_op, panic_call2])

    # These order paths would lead to cycles:
    assert not has_order_path(hugr, pure_call1, panic_call1)
    for op in [panic_op, pure_call2, panic_call2]:
        assert not has_order_path(hugr, op, pure_call1)
    assert not has_order_path(hugr, panic_call2, pure_call2)
    for op in [panic_call1, pure_call1, panic_op]:
        assert not has_order_path(hugr, pure_call2, op)

    # For the time being:
    check_order(hugr, [panic_call1, pure_call1, panic_op, pure_call2, panic_call2])
    pytest.xfail(
        "Calls to nested functions are not resolved in checking,"
        " leading to spurious order edges"
    )

    # Otherwise - the desired outcome when previous is fixed:
    for pure_call in [pure_call1, pure_call2]:
        for op in [panic_call1, panic_op, panic_call2]:
            assert not has_order_path(hugr, pure_call, op)
            assert not has_order_path(hugr, op, pure_call)


def test_decl(validate):
    @guppy.declare
    def foo() -> int: ...

    @guppy
    def bar() -> int:
        return foo()

    @guppy
    def main() -> int:
        return bar()

    pkg = main.with_minimal_opt().compile_function()
    validate(pkg)
    hugr = pkg.modules[0]
    [main_node] = [
        node
        for node, data in hugr.nodes()
        if isinstance(data.op, hops.FuncDefn) and "main" in data.op.f_name
    ]
    [inp, out, call_cfg] = hugr.children(main_node)

    assert isinstance(hugr[inp].op, hops.Input)
    assert isinstance(hugr[out].op, hops.Output)
    [call] = [
        node
        for node in hugr.descendants(call_cfg)
        if isinstance(hugr[node].op, hops.Call)
    ]
    assert "bar" in get_called_func_name(hugr, call)

    check_order(hugr, [inp, call_cfg, out])
