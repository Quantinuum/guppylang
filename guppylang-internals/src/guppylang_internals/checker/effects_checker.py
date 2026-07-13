from typing import TYPE_CHECKING, cast

import networkx as nx

if TYPE_CHECKING:
    from guppylang_internals.engine import MonoDefId
    from guppylang_internals.tys import Effect


def compute_effects() -> None:
    """Computes the effects of functions in the program, checking that they
    respect the declared effect limits. This should be called after a call graph
    has been constructed during checking."""
    from guppylang_internals.engine import ENGINE

    # Then compute strongly components to find cycles in the call graph. Every node
    # in a component must have the same effects.
    call_graph = cast("nx.DiGraph[MonoDefId]", ENGINE.call_graph)
    components = list(nx.strongly_connected_components(call_graph))
    condensed = nx.condensation(call_graph, scc=components)

    # These two store the same info but for access during SCC traversal
    # and for compilation later
    component_effects: dict[int, frozenset[Effect]] = {}

    # Start in the leaves of the condensed graph and work up to the roots, so that we
    # can compute the effects of a component based on the effects of its callees.
    for component in reversed(list(nx.topological_sort(condensed))):
        members = condensed.nodes[component]["members"]
        effects = set.union(
            *(call_graph.nodes[mono_def_id]["effects"] for mono_def_id in members)
        )
        for succ in condensed.successors(component):
            effects.update(component_effects[succ])

        component_effects[component] = frozenset(effects)

        # Apply inferred effects to all members of each component.
        for def_id in members:
            data = call_graph.nodes[def_id]
            data["effects"] = effects
            data["computed"] = True
