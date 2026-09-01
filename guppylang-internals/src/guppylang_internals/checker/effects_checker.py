from collections.abc import Mapping
from typing import TYPE_CHECKING

from guppylang_internals.checker.callgraph import CallGraph, CallGraphComponent
from guppylang_internals.tys import Effect

if TYPE_CHECKING:
    from guppylang_internals.engine import MonoDefId


def compute_effects(
    call_graph: CallGraph,
    other_callee_effects: Mapping["MonoDefId", list[Effect]],
) -> Mapping["MonoDefId", frozenset[Effect]]:
    """Computes the effects of functions in the program, checking that they
    respect the declared effect limits. This should be called after a call graph
    has been constructed during checking."""

    component_effects: dict[CallGraphComponent, frozenset[Effect]] = {}

    # Start in the leaves of the condensed graph and work up to the roots, so that we
    # can compute the effects of a component based on the effects of its callees.
    for component in reversed(call_graph.condensed):
        effects = set.union(
            *(
                set(other_callee_effects[mono_def_id])
                for mono_def_id in component.members
            )
        )
        for _, succ, _ in component.callees:
            effects.update(component_effects[succ])

        fx = frozenset(effects)
        component_effects[component] = fx

    return {
        def_id: component_effects[component]
        for component in call_graph.condensed
        for def_id in component.members
    }
