from dataclasses import FrozenInstanceError

import pytest
from guppylang_internals.analysis.callgraph import CallGraph, ProgramGraph
from guppylang_internals.analysis.modifier import ConcreteCustomUse
from guppylang_internals.checker.modifier import CustomModifierKind
from guppylang_internals.definition.common import DefId
from guppylang_internals.tys.builtin import nat_type
from guppylang_internals.tys.param import ConstParam


@pytest.mark.parametrize("condense_before_mutation", [False, True])
def test_snapshot_isolated_from_source_mutations(condense_before_mutation):
    root, called, loaded = [(DefId.fresh(), ()) for _ in range(3)]
    custom = (DefId.fresh(), ())
    custom_use = ConcreteCustomUse(called, custom, CustomModifierKind.DAGGERED, None)
    custom_uses = {custom: custom_use}
    calls = {root: [called, called], called: [], loaded: []}
    loads = {root: {loaded}, called: set(), loaded: set()}
    graph = ProgramGraph(calls, loads, custom_uses)
    call_graph = CallGraph(graph.call_graph)

    if condense_before_mutation:
        assert len(call_graph.condensed) == 3

    # Change existing rows, replace a row, and remove keys in the source graphs.
    calls[root].append(loaded)
    calls[called].append(root)
    calls[loaded] = [root]
    calls.clear()
    loads[root].clear()
    loads[called].add(root)
    loads[loaded] = {called}
    loads.clear()
    custom_uses.clear()

    assert graph.call_graph == {root: (called, called), called: (), loaded: ()}
    assert graph.load_graph == {
        root: frozenset({loaded}),
        called: frozenset(),
        loaded: frozenset(),
    }
    assert graph.custom_uses_by_mono_def == {custom: custom_use}
    components = {
        member: component
        for component in call_graph.condensed
        for member in component.members
    }
    assert set(components) == {root, called, loaded}
    assert components[root].external_callees == frozenset(
        {(root, components[called], called)}
    )
    assert components[called].external_callees == frozenset()
    assert components[loaded].external_callees == frozenset()


def test_graph_snapshots_are_read_only():
    root, leaf = [(DefId.fresh(), ()) for _ in range(2)]
    custom_use = ConcreteCustomUse(root, leaf, CustomModifierKind.DAGGERED, None)
    graph = ProgramGraph({root: [leaf]}, {root: {leaf}}, {leaf: custom_use})

    with pytest.raises(TypeError):
        graph.call_graph[root] = ()
    with pytest.raises(TypeError):
        graph.load_graph[root] = frozenset()
    with pytest.raises(TypeError):
        graph.custom_uses_by_mono_def[leaf] = custom_use
    with pytest.raises(TypeError):
        graph.call_graph[root][0] = root
    with pytest.raises(AttributeError):
        graph.load_graph[root].add(root)
    with pytest.raises(FrozenInstanceError):
        graph.call_graph = {}
    with pytest.raises(FrozenInstanceError):
        graph.load_graph = {}
    with pytest.raises(FrozenInstanceError):
        graph.custom_uses_by_mono_def = {}

    assert graph.call_graph[root] == (leaf,)
    assert graph.load_graph[root] == frozenset({leaf})
    assert graph.custom_uses_by_mono_def == {leaf: custom_use}


def test_empty_graph():
    graph = ProgramGraph({}, {})

    assert graph.call_graph == {}
    assert graph.load_graph == {}
    assert graph.custom_uses_by_mono_def == {}
    assert CallGraph(graph.call_graph).condensed == []


def test_empty_rows_are_retained():
    root = (DefId.fresh(), ())
    graph = ProgramGraph({root: []}, {root: set()})

    assert graph.call_graph == {root: ()}
    assert graph.load_graph == {root: frozenset()}
    [component] = CallGraph(graph.call_graph).condensed
    assert component.members == frozenset({root})
    assert component.external_callees == frozenset()


def test_load_edges_do_not_contribute_to_call_components():
    root, called, loaded = [(DefId.fresh(), ()) for _ in range(3)]
    graph = ProgramGraph(
        {root: [called], called: [], loaded: []},
        {root: {loaded}, called: {root}, loaded: {root}},
    )

    # Combining call and load edges would put all three functions in one cycle.
    components = {
        member: component
        for component in CallGraph(graph.call_graph).condensed
        for member in component.members
    }
    assert set(components) == {root, called, loaded}
    for member, component in components.items():
        assert component.members == frozenset({member})
    assert components[root].external_callees == frozenset(
        {(root, components[called], called)}
    )
    assert components[called].external_callees == frozenset()
    assert components[loaded].external_callees == frozenset()


def test_recursive_call_components_and_external_callees():
    root, first, second, external = [(DefId.fresh(), ()) for _ in range(4)]
    graph = ProgramGraph(
        {root: [first], first: [second], second: [first, external]}, {}
    )

    root_component, recursive_component = CallGraph(graph.call_graph).condensed
    assert root_component.members == frozenset({root})
    assert recursive_component.members == frozenset({first, second})
    assert root_component.external_callees == frozenset(
        {(root, recursive_component, first)}
    )
    assert recursive_component.external_callees == frozenset({(second, None, external)})


def test_generic_definitions_are_not_call_component_members():
    root = (DefId.fresh(), ())
    generic = (DefId.fresh(), (ConstParam(0, "n", nat_type()).to_bound(),))
    graph = ProgramGraph({root: [generic], generic: [root]}, {})

    assert graph.call_graph[generic] == (root,)
    [component] = CallGraph(graph.call_graph).condensed
    assert component.members == frozenset({root})
    assert component.external_callees == frozenset({(root, None, generic)})
