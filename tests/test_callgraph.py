from copy import deepcopy
from types import SimpleNamespace

import pytest
from guppylang import guppy
from guppylang_internals.analysis.modifier import (
    ConcreteCustomUse,
    analyze_modifier_calls,
)
from guppylang_internals.checker.modifier import (
    NO_CALL_MODIFIERS,
    CustomModifierKind,
    ModifierContext,
)
from guppylang_internals.definition.common import DefId
from guppylang_internals.engine import ENGINE, CompilationStage
from guppylang_internals.error import InternalGuppyError
from guppylang_internals.span import Loc, Span
from guppylang_internals.tys import Effect


@pytest.mark.parametrize("mutation", ["load", "call", "effects", "node"])
def test_call_info_mutation_invalidates_analysis(mutation):
    @guppy
    def root() -> int:
        return 42

    root.check()
    assert ENGINE.analyzed_graph is not None
    mono_id = (root.id, ())

    match mutation:
        case "load":
            ENGINE.register_load(mono_id, mono_id)
        case "call":
            callee = ENGINE.get_parsed(root.id)
            ctx = SimpleNamespace(
                current_caller=mono_id, modifier_ctx=NO_CALL_MODIFIERS
            )
            ENGINE.register_call(ctx, callee, (), callee.defined_at)
        case "effects":
            ENGINE.register_effects(mono_id, [Effect.PANIC])
        case "node":
            ENGINE.register_call_graph_node((DefId.fresh(), ()))

    assert ENGINE.analyzed_graph is None
    with (
        ENGINE._in_stage(CompilationStage.COMPILE),
        pytest.raises(AssertionError, match="analyzed_graph is None"),
    ):
        ENGINE._compile_impl([root.id], "dummy context")


def test_lazy_check_invalidates_analysis_and_compile_recomputes_it():
    @guppy
    def first() -> int:
        return 1

    @guppy
    def second() -> int:
        return 2

    first.check()
    original_analysis = ENGINE.analyzed_graph
    assert original_analysis is not None
    ENGINE.get_checked(first.id, ())
    assert ENGINE.analyzed_graph is original_analysis

    ENGINE.get_checked(second.id, ())
    assert ENGINE.analyzed_graph is None
    ENGINE.compile([first.id, second.id], reset=False)
    assert ENGINE.analyzed_graph is not None
    assert ENGINE.analyzed_graph is not original_analysis
    assert (second.id, ()) in ENGINE.analyzed_graph.call_graph


def test_compilation_rejects_call_info_mutation(monkeypatch):
    from guppylang_internals.compiler.core import CompilerContext

    @guppy
    def root() -> int:
        return 42

    iterate_worklist = CompilerContext.iterate_worklist

    def mutate_after_lowering(ctx):
        # Run normal lowering, then change call information to trigger the guard.
        iterate_worklist(ctx)
        ENGINE.register_effects((root.id, ()), [Effect.PANIC])

    monkeypatch.setattr(CompilerContext, "iterate_worklist", mutate_after_lowering)
    with pytest.raises(InternalGuppyError, match="Call information changed"):
        ENGINE.compile([root.id])


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
    root_data = ENGINE.call_info.call_graph.get((root.id, ()))
    assert root_data is not None
    caller1_data = ENGINE.call_info.call_graph.get((caller1.id, ()))
    assert caller1_data is not None
    caller2_data = ENGINE.call_info.call_graph.get((caller2.id, ()))
    assert caller2_data is not None
    assert (leaf.id, ()) in ENGINE.call_info.call_graph
    assert ENGINE.call_info.call_graph.get((leaf_decl.id, ())) is None

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
    # factorial calls itself
    assert mono_id in ENGINE.call_info.call_graph[mono_id]


def test_nested_function():
    """Test that nested function calls are recorded in the call graph."""

    @guppy
    def outer() -> int:
        @guppy
        def inner() -> int:
            return 42

        return inner()

    outer.check()

    data = ENGINE.call_info.call_graph.get((outer.id, ()))
    assert data is not None
    # Check the outer function calls exactly one function (the nested function).
    assert len(data) == 1


def test_analysis_returns_graph_without_mutating_checking_data():
    root, helper, gate, custom, loaded = [(DefId.fresh(), ()) for _ in range(5)]
    controlled = ModifierContext(control_sizes=(1,))
    span = Span(Loc(__file__, 1, 1), Loc(__file__, 1, 2))
    custom_use = ConcreteCustomUse(gate, custom, CustomModifierKind.CONTROLLED, 1)
    calls = {
        root: [helper],
        helper: [gate, gate],
        gate: [],
        custom: [],
        loaded: [gate],
    }
    loads = {
        root: set(),
        helper: {loaded},
        gate: set(),
        custom: {loaded},
        loaded: set(),
    }
    local_modifiers = {
        (root, helper): {controlled: span},
        (helper, gate): {NO_CALL_MODIFIERS: span},
        (loaded, gate): {NO_CALL_MODIFIERS: span},
    }
    original_inputs = deepcopy((calls, loads, local_modifiers))

    def resolve(callee, context):
        if callee == gate and context == controlled:
            return custom, custom_use
        return callee, None

    result = analyze_modifier_calls([root], calls, loads, local_modifiers, resolve)

    assert (calls, loads, local_modifiers) == original_inputs
    assert result.call_graph == {
        root: (helper,),
        helper: (custom,),
        gate: (),
        custom: (),
        loaded: (gate,),
    }
    assert result.load_graph == {
        root: frozenset(),
        helper: frozenset({loaded}),
        gate: frozenset(),
        custom: frozenset({loaded}),
        loaded: frozenset(),
    }
    assert result.custom_uses_by_mono_def == {custom: custom_use}
