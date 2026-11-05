"""Tests for the graphs returned by context-sensitive modifier analysis."""

from copy import deepcopy

import pytest
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
from guppylang_internals.span import Loc, Span


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
    assert result.program_graph.call_graph == {
        root: (helper,),
        helper: (custom,),
        gate: (),
        custom: (),
        loaded: (gate,),
    }
    assert result.program_graph.load_graph == {
        root: frozenset(),
        helper: frozenset({loaded}),
        gate: frozenset(),
        custom: frozenset({loaded}),
        loaded: frozenset(),
    }
    assert result.resolved_calls[(helper, gate), controlled] == custom
    # Loading a function does not pass on the helper's inherited control context.
    assert result.resolved_calls[(loaded, gate), NO_CALL_MODIFIERS] == gate
    assert result.program_graph.custom_uses_by_mono_def == {custom: custom_use}


def test_analysis_includes_newly_checked_custom_dependencies():
    root, gate, custom, factory, loaded, leaf = [(DefId.fresh(), ()) for _ in range(6)]
    daggered = ModifierContext(daggered=True)
    span = Span(Loc(__file__, 1, 1), Loc(__file__, 1, 2))
    custom_use = ConcreteCustomUse(gate, custom, CustomModifierKind.DAGGERED, None)
    calls = {root: [gate], gate: []}
    loads = {root: set(), gate: set()}
    local_modifiers = {(root, gate): {daggered: span}}

    def resolve(callee, context):
        if callee == gate and context == daggered:
            return custom, custom_use
        return callee, None

    first = analyze_modifier_calls([root], calls, loads, local_modifiers, resolve)
    assert first.program_graph.call_graph[root] == (custom,)
    assert custom not in first.program_graph.call_graph

    # Simulate draining the checking worklists before the next analysis pass.
    calls.update({custom: [], factory: [], loaded: [leaf], leaf: []})
    loads.update({custom: {factory}, factory: {loaded}, loaded: set(), leaf: set()})
    second = analyze_modifier_calls([root], calls, loads, local_modifiers, resolve)

    assert second.program_graph.call_graph == {
        root: (custom,),
        gate: (),
        custom: (),
        factory: (),
        loaded: (leaf,),
        leaf: (),
    }
    assert second.program_graph.load_graph == {
        root: frozenset(),
        gate: frozenset(),
        custom: frozenset({factory}),
        factory: frozenset({loaded}),
        loaded: frozenset(),
        leaf: frozenset(),
    }
    assert second.resolved_calls[(loaded, leaf), NO_CALL_MODIFIERS] == leaf
    assert second.program_graph.custom_uses_by_mono_def == {custom: custom_use}
    assert first.program_graph.call_graph == {root: (custom,), gate: ()}
    assert first.program_graph.load_graph == {root: frozenset(), gate: frozenset()}


@pytest.mark.parametrize("collection_type", [set, frozenset, tuple, list])
def test_analysis_preserves_load_collections(collection_type):
    root, loaded, leaf = [(DefId.fresh(), ()) for _ in range(3)]
    loads = {
        root: collection_type([loaded]),
        loaded: collection_type(),
        leaf: collection_type(),
    }
    original_loads = deepcopy(loads)
    result = analyze_modifier_calls(
        [root],
        {root: [], loaded: [leaf], leaf: []},
        loads,
        {},
        lambda callee, _context: (callee, None),
    )

    assert loads == original_loads
    assert result.program_graph.call_graph == {root: (), loaded: (leaf,), leaf: ()}
    assert result.program_graph.load_graph == {
        root: frozenset({loaded}),
        loaded: frozenset(),
        leaf: frozenset(),
    }
    assert result.resolved_calls[(loaded, leaf), NO_CALL_MODIFIERS] == leaf
