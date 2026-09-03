"""Integration tests for modifier-labelled call-graph analysis."""

from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.builtins import dagger, control, panic
from guppylang.std.quantum import discard, discard_array, qubit
from guppylang_internals.checker.callgraph import CallGraph
from guppylang_internals.checker.effects_checker import compute_effects
from guppylang_internals.checker.modifier import CustomModifierKind
from guppylang_internals.definition.function import CompiledFunctionDef
from guppylang_internals.engine import DEF_STORE, ENGINE
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
    main_callees = set(ENGINE.call_graph[main_id])
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
    effects = compute_effects(CallGraph(ENGINE.call_graph), ENGINE.other_callee_effects)

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
    ENGINE.call_graph[implementation].append(implementation)

    effects = compute_effects(CallGraph(ENGINE.call_graph), ENGINE.other_callee_effects)
    assert implementation in ENGINE.call_graph[implementation]
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
