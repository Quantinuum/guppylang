from collections.abc import Mapping
from typing import TYPE_CHECKING

from guppylang_internals.checker.callgraph import CallGraph
from guppylang_internals.tys import Effect

if TYPE_CHECKING:
    from guppylang_internals.engine import MonoDefId


def compute_effects(
    call_graph: CallGraph,
    other_callee_effects: Mapping["MonoDefId", set[Effect]],
) -> Mapping["MonoDefId", frozenset[Effect]]:
    """Computes the effects of functions in the program, checking that they
    respect the declared effect limits. This should be called after a call graph
    has been constructed during checking."""

    func_effects: dict[MonoDefId, frozenset[Effect]] = {}

    # Start in the leaves of the condensed graph and work up to the roots, so that we
    # can compute the effects of a component based on the effects of its callees.
    for component in reversed(call_graph.condensed):
        effects = set.union(
            *(set(other_callee_effects[func]) for func in component.members)
        )
        for _, _, tgt in component.callees:
            effects.update(func_effects[tgt])
        func_effects.update(dict.fromkeys(component.members, frozenset(effects)))

    return func_effects
