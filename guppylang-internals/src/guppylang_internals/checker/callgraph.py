from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING

import networkx as nx

from guppylang_internals.tys.subst import BoundVarFinder

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from guppylang_internals.engine import MonoDefId


class CallGraph:
    _all_calls: Mapping[MonoDefId, Iterable[MonoDefId]]
    _graph: nx.DiGraph[MonoDefId]

    @cached_property
    def condensed(self) -> Sequence[CallGraphComponent]:
        """Returns a list of SCCs of the call graph, in topological sort order
        (caller before callee)."""
        components = list(nx.strongly_connected_components(self._graph))
        condensed = nx.condensation(self._graph, scc=components)

        rev_result = []
        comps: dict[MonoDefId, CallGraphComponent] = {}
        # Process callees first
        for component in reversed(list(nx.topological_sort(condensed))):
            members: frozenset[MonoDefId] = frozenset(
                condensed.nodes[component]["members"]
            )
            cgc = CallGraphComponent(
                members=members,
                external_callees=frozenset(
                    (src, comps[tgt] if tgt in self._graph.nodes else None, tgt)
                    for src in members
                    for tgt in self._all_calls[src]
                    if tgt not in members
                ),
            )
            comps.update(dict.fromkeys(members, cgc))
            rev_result.append(cgc)
        return list(reversed(rev_result))

    def __init__(self, calls: Mapping[MonoDefId, Iterable[MonoDefId]]):
        self._all_calls = calls  # deepcopy?
        self._graph = nx.DiGraph()
        for mono_def_id in calls:
            if is_concrete(
                mono_def_id
            ):  # Only concrete functions will actually be compiled
                self._graph.add_node(mono_def_id)

        for mono_def_id, callees in calls.items():
            if mono_def_id not in self._graph.nodes:
                continue
            for tgt in callees:
                if tgt in self._graph.nodes:
                    self._graph.add_edge(mono_def_id, tgt)


def is_concrete(mono_def_id: MonoDefId) -> bool:
    """Returns True if the given monomorphized definition is concrete
    (i.e. does not contain any BoundVar's)."""
    finder = BoundVarFinder()
    (_, args) = mono_def_id
    for arg in args:
        arg.visit(finder)
    return not (bool(finder.bound_vars))


@dataclass(frozen=True)
class CallGraphComponent:
    """Represents a strongly connected component in the call graph."""

    members: frozenset[MonoDefId]

    """ Calls from functions in this component to functions outside it.
    Each tuple is (source, target component, target), with the target component being
    None if the target is not in the call graph."""
    external_callees: frozenset[tuple[MonoDefId, CallGraphComponent | None, MonoDefId]]
