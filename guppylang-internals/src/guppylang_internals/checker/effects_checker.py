from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import networkx as nx

from guppylang_internals.ast_util import AstNode
from guppylang_internals.tys import Effect

if TYPE_CHECKING:
    from guppylang_internals.engine import MonoDefId


@dataclass
class CallGraphData:
    """Node in the call graph representing a function with its effect limit
    declaration."""

    # calls to definitions, each with AST of the call
    callee_defs: list[tuple["MonoDefId", AstNode]] = field(default_factory=list)
    other_callee_effects: list[Effect] = field(default_factory=list)


def compute_effects() -> Mapping["MonoDefId", frozenset[Effect]]:
    """Computes the effects of functions in the program, checking that they
    respect the declared effect limits. This should be called after a call graph
    has been constructed during checking."""
    from guppylang_internals.engine import ENGINE

    # First construct a networkx DiGraph based on the call graph info for analysis.
    call_info = ENGINE.call_graph
    call_graph = nx.DiGraph(
        (caller_id, callee)
        for caller_id, info in call_info.items()
        for callee, _ in info.callee_defs
    )

    # Then compute strongly components to find cycles in the call graph. Every node
    # in a component must have the same effects.
    components = list(nx.strongly_connected_components(call_graph))
    condensed = nx.condensation(call_graph, scc=components)

    # These two store the same info but for access during graph traversal
    # and for compilation later
    component_effects: dict[int, frozenset[Effect]] = {}
    mapping: dict[MonoDefId, frozenset[Effect]] = {}

    # Start in the leaves of the condensed graph and work up to the roots, so that we
    # can compute the effects of a component based on the effects of its callees.
    for component in reversed(list(nx.topological_sort(condensed))):
        members = condensed.nodes[component]["members"]
        effects = frozenset.union(
            *(component_effects[succ] for succ in condensed.successors(component))
        ).union(*(call_info[def_id].other_callee_effects for def_id in members))

        component_effects[component] = effects

        # Apply inferred effects to all members of each component.
        for def_id in members:
            mapping[def_id] = effects
    return mapping
