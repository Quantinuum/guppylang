from collections.abc import Mapping
from typing import TYPE_CHECKING

import networkx as nx

from guppylang_internals.tys import Effect
from guppylang_internals.tys.subst import BoundVarFinder

if TYPE_CHECKING:
    from guppylang_internals.engine import MonoDefId


def compute_effects(
    callee_defs: Mapping["MonoDefId", list["MonoDefId"]],
    other_callee_effects: Mapping["MonoDefId", list[Effect]],
) -> Mapping["MonoDefId", frozenset[Effect]]:
    """Computes the effects of functions in the program, checking that they
    respect the declared effect limits. This should be called after a call graph
    has been constructed during checking."""

    # First construct a networkx DiGraph based on the call graph info for analysis.
    call_graph: nx.DiGraph[MonoDefId] = nx.DiGraph()
    for mono_def_id in callee_defs:
        finder = BoundVarFinder()
        (_, args) = mono_def_id
        # Include only real/concrete instantiations, the others will not be compiled.
        for arg in args:
            arg.visit(finder)
        if not finder.bound_vars:
            call_graph.add_node(mono_def_id)

    for mono_def_id, callees in callee_defs.items():
        if mono_def_id not in call_graph.nodes:
            continue
        effects = set(other_callee_effects[mono_def_id])
        for tgt in callees:
            assert tgt in call_graph.nodes
            call_graph.add_edge(mono_def_id, tgt)
        call_graph.nodes[mono_def_id]["effects"] = effects

    # Then compute strongly components to find cycles in the call graph. Every node
    # in a component must have the same effects.
    components = list(nx.strongly_connected_components(call_graph))
    condensed = nx.condensation(call_graph, scc=components)

    # These two store the same info but for access during SCC traversal
    # and for compilation later
    component_effects: dict[int, frozenset[Effect]] = {}
    mapping: dict[MonoDefId, frozenset[Effect]] = {}

    # Start in the leaves of the condensed graph and work up to the roots, so that we
    # can compute the effects of a component based on the effects of its callees.
    for component in reversed(list(nx.topological_sort(condensed))):
        members = condensed.nodes[component]["members"]
        effects = set.union(
            *(call_graph.nodes[mono_def_id]["effects"] for mono_def_id in members)
        )
        for succ in condensed.successors(component):
            effects.update(component_effects[succ])

        fx = frozenset(effects)
        component_effects[component] = fx

        # Apply inferred effects to all members of each component.
        for def_id in members:
            mapping[def_id] = fx

    return mapping
