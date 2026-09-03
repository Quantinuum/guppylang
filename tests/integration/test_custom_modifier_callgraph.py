"""Integration tests for modifier-labelled call-graph analysis."""

from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.builtins import control, dagger, nat, panic
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
from guppylang_internals.tys.subst import is_concrete_inst


@guppy.unitary
class _same_count_recursive_gate:
    n = guppy.nat_var("n")

    @guppy
    def __call__(q: qubit) -> None:
        pass

    @guppy
    def controlled(q: qubit, controls: array[qubit, n]) -> None:
        _same_count_helper(q, controls)


@guppy
def _same_count_helper[n: nat](q: qubit, controls: array[qubit, n]) -> None:
    with control(controls):
        _same_count_recursive_gate(q)


def test_custom_modifier_monomorphizations(use_experimental_features):
    """Custom methods are checked eagerly and concretely monomorphized on demand."""

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

    unused.with_minimal_opt().compile_function()
    assert any(
        def_id == controlled_id and not is_concrete_inst(mono_args)
        for def_id, mono_args in ENGINE.checked
    )
    assert concrete_controlled.isdisjoint(ENGINE.checked)
    assert not ENGINE.custom_uses_by_mono_def
    assert all(def_id != controlled_id for def_id, _ in ENGINE.compiled)

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
        for modifiers in ENGINE.modifiers_ctx_by_edges[original_edge]
    } == {1, 2}
    assert len(ENGINE.modifiers_ctx_by_edges[original_edge]) == 3
    assert {
        ENGINE.resolved_modified_calls[(original_edge, modifier_ctx)]
        for modifier_ctx in ENGINE.modifiers_ctx_by_edges[original_edge]
    } == concrete_controlled
    assert set(ENGINE.custom_uses_by_mono_def) == concrete_controlled
    assert ENGINE._discover_concrete_custom_uses() == []
    for custom_def, custom_use in ENGINE.custom_uses_by_mono_def.items():
        assert custom_use.unmodified_callee == (custom_gate.id, ())
        assert custom_use.custom_def == custom_def
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

    [custom_use] = ENGINE.custom_uses_by_mono_def.values()
    assert effects[custom_use.unmodified_callee] == frozenset({Effect.ANY})
    assert effects[custom_use.custom_def] == frozenset()
    assert effects[custom_main.id, ()] == frozenset()
    assert effects[fallback_main.id, ()] == frozenset({Effect.ANY})


def test_recursive_custom_modifier_effects(use_experimental_features):
    """Recursive custom definitions participate in effect SCC analysis."""

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
    [custom_use] = ENGINE.custom_uses_by_mono_def.values()
    custom_def = custom_use.custom_def
    # Model recursion on the concrete custom definition. A unitary class cannot
    # currently refer to its enclosing class name from inside the class-body frame.
    ENGINE.call_graph[custom_def].append(custom_def)

    effects = compute_effects(CallGraph(ENGINE.call_graph), ENGINE.other_callee_effects)
    assert custom_def in ENGINE.call_graph[custom_def]
    assert effects[custom_def] == frozenset({Effect.ANY})
    assert effects[main.id, ()] == frozenset({Effect.ANY})


def test_recursive_custom_modifier_same_control_count(use_experimental_features):
    """Indirect recursion at the same control count reaches a fixed point."""

    @guppy
    def main(q: qubit, c: qubit) -> None:
        with control(c):
            _same_count_recursive_gate(q)

    main.check()

    [custom_use] = ENGINE.custom_uses_by_mono_def.values()
    custom_def = custom_use.custom_def
    helper_instantiation = (
        _same_count_helper.id,
        (ConstArg(ConstValue(nat_type(), 1)),),
    )

    assert custom_use.control_count == 1
    assert helper_instantiation in ENGINE.call_graph[custom_def]
    assert custom_def in ENGINE.call_graph[helper_instantiation]


def test_non_recursive_control_count_increase_is_allowed(use_experimental_features):
    """Different non-recursive paths may use increasing control counts."""

    @guppy.unitary
    class custom_gate:
        n = guppy.nat_var("n")

        @guppy
        def __call__(q: qubit) -> None:
            pass

        @guppy
        def controlled(q: qubit, _controls: array[qubit, n]) -> None:
            pass

    @guppy
    def call_with_one_control(q: qubit, c: qubit) -> None:
        with control(c):
            custom_gate(q)

    @guppy
    def call_with_two_controls(q: qubit, controls: array[qubit, 2]) -> None:
        with control(controls):
            custom_gate(q)

    @guppy
    def main(q: qubit, c: qubit, controls: array[qubit, 2]) -> None:
        call_with_one_control(q, c)
        call_with_two_controls(q, controls)

    main.check()

    assert {use.control_count for use in ENGINE.custom_uses_by_mono_def.values()} == {
        1,
        2,
    }


def test_custom_modifier_compilation_metadata(use_experimental_features):
    """Only discovered custom definitions are compiled and linked in metadata."""

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

    unmodified_def = ENGINE.compiled[custom_gate.id, ()]
    assert isinstance(unmodified_def, CompiledFunctionDef)
    unmodified_metadata = hugr[unmodified_def.hugr_node].metadata

    custom_uses = list(ENGINE.custom_uses_by_mono_def.values())
    assert len(custom_uses) == 4
    custom_def_ids = set(DEF_STORE.custom_modified_defs[custom_gate.id].values())
    assert {mono_id for mono_id in ENGINE.compiled if mono_id[0] in custom_def_ids} == {
        use.custom_def for use in custom_uses
    }

    links_by_kind: dict[CustomModifierKind, list[tuple[int | None, str]]] = {}
    for custom_use in custom_uses:
        compiled = ENGINE.compiled[custom_use.custom_def]
        assert isinstance(compiled, CompiledFunctionDef)
        links_by_kind.setdefault(custom_use.kind, []).append(
            (
                custom_use.control_count,
                compiled.link_name,
            )
        )
        custom_metadata = hugr[compiled.hugr_node].metadata
        if custom_use.control_count is not None:
            assert custom_metadata[NUM_CONTROL_QUBITS_KEY] == custom_use.control_count

    assert (
        unmodified_metadata[DAGGERED_KEY]
        == links_by_kind[CustomModifierKind.DAGGERED][0][1]
    )
    assert unmodified_metadata[CONTROLLED_KEY] == [
        link for _, link in sorted(links_by_kind[CustomModifierKind.CONTROLLED])
    ]
    assert unmodified_metadata[CTRL_DAGGERED_KEY] == [
        links_by_kind[CustomModifierKind.CTRL_DAGGERED][0][1]
    ]


def test_custom_modifier_metadata_is_per_unmodified_callee(
    use_experimental_features,
):
    """Modifier links do not leak between unmodified callee monomorphizations."""

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

    unmodified_callee_ids = {
        mono_id for mono_id in ENGINE.compiled if mono_id[0] == custom_gate.id
    }
    assert len(unmodified_callee_ids) == 2
    for unmodified_callee in unmodified_callee_ids:
        [custom_use] = [
            use
            for use in ENGINE.custom_uses_by_mono_def.values()
            if use.unmodified_callee == unmodified_callee
        ]
        unmodified_def = ENGINE.compiled[unmodified_callee]
        custom_def = ENGINE.compiled[custom_use.custom_def]
        assert isinstance(unmodified_def, CompiledFunctionDef)
        assert isinstance(custom_def, CompiledFunctionDef)
        assert hugr[unmodified_def.hugr_node].metadata[CONTROLLED_KEY] == [
            custom_def.link_name
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

    modifier_contexts = ENGINE.modifiers_ctx_by_edges.get(
        (
            (root.id, ()),
            (leaf.id, ()),
        )
    )
    assert modifier_contexts is not None
    assert len(modifier_contexts) == 2
    [unmodified] = [m for m in modifier_contexts if not m.control_sizes]
    [modifiers] = [m for m in modifier_contexts if m.control_sizes]
    assert not unmodified.daggered
    assert modifiers.daggered
    assert modifiers.control_sizes == (1, 1)
    assert modifiers.concrete_control_count() == 2
    assert modifier_contexts[unmodified] is not None
    assert modifier_contexts[modifiers] is not None
