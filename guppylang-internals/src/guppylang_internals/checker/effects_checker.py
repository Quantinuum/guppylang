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
            *(other_callee_effects.get(func, set()) for func in component.members),
            *(
                # If the callee is in the call graph, use its computed effects;
                # otherwise (a leaf) use only the effects gathered directly by checking.
                func_effects[tgt] if cmp is not None else other_callee_effects[tgt]
                for func, cmp, tgt in component.external_callees
            ),
        )
        func_effects.update(dict.fromkeys(component.members, frozenset(effects)))

    return func_effects
