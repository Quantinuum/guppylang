import pytest
from hugr import ops as hops
from hugr import InPort
from hugr.std import PRELUDE

from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.builtins import dagger, control, owned, panic
from guppylang.std.quantum import discard, discard_array, qubit
from guppylang_internals.checker.effects_checker import compute_effects
from guppylang_internals.definition.function import CompiledFunctionDef
from guppylang_internals.engine import DEF_STORE, ENGINE, CustomModifierKind
from guppylang.std.quantum.functional import cx, h
from guppylang_internals.metadata.common import (
    CONTROLLED_KEY,
    CTRL_DAGGERED_KEY,
    DAGGERED_KEY,
    NUM_CONTROL_QUBITS_KEY,
)
from guppylang_internals.tys import Effect
from guppylang_internals.tys.arg import ConstArg
from guppylang_internals.tys.builtin import nat_type
from guppylang_internals.tys.const import ConstValue


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


def test_custom_modifier_monomorphizations(use_experimental_features):
    """Only concrete custom implementations required by labelled calls are checked."""

    @guppy.unitary
    class custom_gate:
        n = guppy.nat_var("n")

        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled(q: qubit, _controls: array[qubit, n]) -> None:
            pass

    custom_defs = DEF_STORE.custom_modified_defs[custom_gate.id]
    controlled_id = custom_defs[CustomModifierKind.CONTROLLED]
    concrete_controlled = {
        (
            controlled_id,
            (ConstArg(ConstValue(nat_type(), control_count)),),
        )
        for control_count in (1, 2)
    }

    @guppy
    def unused() -> None:
        q = qubit()
        custom_gate(q)
        discard(q)

    unused.check()
    # todo: check instead that the general
    assert concrete_controlled.isdisjoint(ENGINE.checked)
    assert not ENGINE.concrete_custom_uses

    @guppy
    def main() -> None:
        q = qubit()
        control1 = qubit()
        control2 = qubit()
        controls2 = array(qubit(), qubit())
        with control(control1):
            custom_gate(q)
        with control(control1), control(control2):
            custom_gate(q)
        with control(controls2):
            custom_gate(q)
        discard(q)
        discard(control1)
        discard(control2)
        discard_array(controls2)

    main.check()

    assert concrete_controlled <= ENGINE.checked.keys()

    main_id = (main.id, ())
    original_edge = (main_id, (custom_gate.id, ()))
    assert {
        modifiers.concrete_control_count()
        for modifiers in ENGINE.modifiers_on_calls[original_edge]
    } == {1, 2}
    assert len(ENGINE.modifiers_on_calls[original_edge]) == 3
    assert {
        ENGINE.resolved_call_targets[(original_edge, modifier_ctx)]
        for modifier_ctx in ENGINE.modifiers_on_calls[original_edge]
    } == concrete_controlled
    assert set(ENGINE.concrete_custom_uses) == concrete_controlled
    assert ENGINE._discover_concrete_custom_uses() == []
    for implementation, custom_use in ENGINE.concrete_custom_uses.items():
        assert custom_use.parent == (custom_gate.id, ())
        assert custom_use.implementation == implementation
        assert custom_use.kind == CustomModifierKind.CONTROLLED
        assert custom_use.control_count in {1, 2}
    main_callees = set(ENGINE.call_graph[main_id].callee_defs)
    assert concrete_controlled <= main_callees
    assert (custom_gate.id, ()) not in main_callees


def test_custom_modifier_effects_use_expanded_call_graph(
    use_experimental_features,
):
    """Effects follow a custom target, while ordinary calls keep their target."""

    @guppy.unitary
    class custom_gate:
        n = guppy.nat_var("n")

        @guppy
        def __call__(q: qubit) -> None:
            panic("parent effect")

        @guppy
        def controlled(q: qubit, _controls: array[qubit, n]) -> None:
            pass

    @guppy
    def fallback() -> None:
        panic("fallback effect")

    @guppy
    def custom_main(q: qubit, c: qubit) -> None:
        with control(c):
            custom_gate(q)

    @guppy
    def fallback_main() -> None:
        fallback()

    ENGINE.check([custom_main.id, fallback_main.id])
    effects = compute_effects(ENGINE.call_graph)

    [custom_use] = ENGINE.concrete_custom_uses.values()
    assert effects[custom_use.parent] == frozenset({Effect.ANY})
    assert effects[custom_use.implementation] == frozenset()
    assert effects[custom_main.id, ()] == frozenset()
    assert effects[fallback_main.id, ()] == frozenset({Effect.ANY})


def test_recursive_custom_modifier_effects(use_experimental_features):
    """Recursive custom implementations participate in effect SCC analysis."""

    @guppy.unitary
    class recursive_gate:
        n = guppy.nat_var("n")

        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled(q: qubit, controls: array[qubit, n]) -> None:
            panic("recursive custom effect")

    @guppy
    def main(q: qubit, c: qubit) -> None:
        with control(c):
            recursive_gate(q)

    main.check()
    [custom_use] = ENGINE.concrete_custom_uses.values()
    implementation = custom_use.implementation
    # Model recursion on the concrete custom implementation. A unitary class cannot
    # currently refer to its enclosing class name from inside the class-body frame.
    ENGINE.call_graph[implementation].callee_defs.append(implementation)

    effects = compute_effects(ENGINE.call_graph)
    assert implementation in ENGINE.call_graph[implementation].callee_defs
    assert effects[implementation] == frozenset({Effect.ANY})
    assert effects[main.id, ()] == frozenset({Effect.ANY})


def test_custom_modifier_compilation_metadata(use_experimental_features):
    """Only discovered custom implementations are compiled and linked in metadata."""

    @guppy.unitary
    class custom_gate:
        n = guppy.nat_var("n")

        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def daggered(q: qubit) -> None:
            pass

        @guppy
        def controlled(q: qubit, controls: array[qubit, n]) -> None:
            pass

        @guppy
        def ctrl_daggered(q: qubit, controls: array[qubit, n]) -> None:
            pass

    @guppy
    def main(q: qubit, c: qubit, controls: array[qubit, 2]) -> None:
        with dagger:
            custom_gate(q)
        with control(c):
            custom_gate(q)
        with control(controls):
            custom_gate(q)
        with control(c), dagger:
            custom_gate(q)

    package = main.with_minimal_opt().compile_function()
    hugr = package.modules[0]

    parent = ENGINE.compiled[custom_gate.id, ()]
    assert isinstance(parent, CompiledFunctionDef)
    parent_metadata = hugr[parent.hugr_node].metadata

    custom_uses = list(ENGINE.concrete_custom_uses.values())
    assert len(custom_uses) == 4
    custom_def_ids = set(DEF_STORE.custom_modified_defs[custom_gate.id].values())
    assert {mono_id for mono_id in ENGINE.compiled if mono_id[0] in custom_def_ids} == {
        use.implementation for use in custom_uses
    }

    links_by_kind: dict[CustomModifierKind, list[tuple[int | None, str]]] = {}
    for custom_use in custom_uses:
        compiled = ENGINE.compiled[custom_use.implementation]
        assert isinstance(compiled, CompiledFunctionDef)
        links_by_kind.setdefault(custom_use.kind, []).append(
            (custom_use.control_count, compiled.link_name)
        )
        custom_metadata = hugr[compiled.hugr_node].metadata
        if custom_use.control_count is not None:
            assert custom_metadata[NUM_CONTROL_QUBITS_KEY] == custom_use.control_count

    assert (
        parent_metadata[DAGGERED_KEY]
        == links_by_kind[CustomModifierKind.DAGGERED][0][1]
    )
    assert parent_metadata[CONTROLLED_KEY] == [
        link for _, link in sorted(links_by_kind[CustomModifierKind.CONTROLLED])
    ]
    assert parent_metadata[CTRL_DAGGERED_KEY] == [
        links_by_kind[CustomModifierKind.CTRL_DAGGERED][0][1]
    ]


def test_custom_modifier_metadata_is_per_parent_monomorphization(
    use_experimental_features,
):
    """Modifier links do not leak between parent monomorphizations."""

    @guppy.unitary
    class custom_gate:
        n = guppy.nat_var("n")
        c = guppy.nat_var("c")

        @guppy
        def __call__(targets: array[qubit, n]) -> None:
            pass

        @guppy
        def controlled(targets: array[qubit, n], controls: array[qubit, c]) -> None:
            pass

    @guppy
    def main(
        targets1: array[qubit, 1],
        targets2: array[qubit, 2],
        control1: qubit,
        controls2: array[qubit, 2],
    ) -> None:
        with control(control1):
            custom_gate(targets1)
        with control(controls2):
            custom_gate(targets2)

    package = main.with_minimal_opt().compile_function()
    hugr = package.modules[0]

    parent_mono_ids = {
        mono_id for mono_id in ENGINE.compiled if mono_id[0] == custom_gate.id
    }
    assert len(parent_mono_ids) == 2
    for parent_mono_id in parent_mono_ids:
        [custom_use] = [
            use
            for use in ENGINE.concrete_custom_uses.values()
            if use.parent == parent_mono_id
        ]
        parent = ENGINE.compiled[parent_mono_id]
        implementation = ENGINE.compiled[custom_use.implementation]
        assert isinstance(parent, CompiledFunctionDef)
        assert isinstance(implementation, CompiledFunctionDef)
        assert hugr[parent.hugr_node].metadata[CONTROLLED_KEY] == [
            implementation.link_name
        ]


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


def test_modifier_labels():
    """Calls are labelled with their complete nested modifier context."""

    @guppy(unitary=True)
    def leaf(q: qubit) -> None:
        pass

    @guppy
    def root(q: qubit, c1: qubit, c2: qubit) -> None:
        leaf(q)
        leaf(q)
        with control(c1):
            with control(c2), dagger:
                leaf(q)

    root.check()

    modifier_contexts = ENGINE.modifiers_on_calls.get(((root.id, ()), (leaf.id, ())))
    assert modifier_contexts is not None
    assert len(modifier_contexts) == 2
    [unmodified] = [m for m in modifier_contexts if not m.control_sizes]
    [modifiers] = [m for m in modifier_contexts if m.control_sizes]
    assert not unmodified.daggered
    assert modifiers.daggered
    assert modifiers.control_sizes == (1, 1)
    assert modifiers.concrete_control_count() == 2
    assert modifier_contexts[unmodified] is None
    assert modifier_contexts[modifiers] is None


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
