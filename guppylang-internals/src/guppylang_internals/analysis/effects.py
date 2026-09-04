from collections.abc import Mapping
from typing import TYPE_CHECKING

from guppylang_internals.analysis.callgraph import CallGraph
from guppylang_internals.tys import Effect

if TYPE_CHECKING:
    from guppylang_internals.engine import MonoDefId


def compute_effects(
    call_graph: CallGraph,
    func_effects: Mapping["MonoDefId", set[Effect]],
) -> Mapping["MonoDefId", frozenset[Effect]]:
    """Computes the effects of functions in the program, given a call graph
    containing a node for exactly those functions for which we wish effects to be
    computed, and func_effects containing an entry for *at least* any callees
    that are not nodes (may also contain entries for calless that are nodes)."""

    computed_effects: dict[MonoDefId, frozenset[Effect]] = {}

    # Start in the leaves of the condensed graph and work up to the roots, so that we
    # can compute the effects of a component based on the effects of its callees.
    for component in reversed(call_graph.condensed):
        # Every node in a component will receive the same effects (the tightest-possible
        # least-upper-bound if we assume every call may occur).
        effects = set.union(
            *(func_effects.get(func, set()) for func in component.members),
            *(
                # If the callee is in the call graph, use its computed effects;
                # otherwise (a leaf) use only the effects gathered directly by checking.
                computed_effects[tgt] if cmp is not None else func_effects[tgt]
                for func, cmp, tgt in component.external_callees
            ),
        )
        computed_effects.update(dict.fromkeys(component.members, frozenset(effects)))

    return computed_effects
