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
            members = frozenset(condensed.nodes[component]["members"])
            cgc = CallGraphComponent(
                members=members,
                callees=frozenset(
                    (src, comps[tgt], tgt)
                    for src in members
                    for tgt in self._graph.successors(src)
                    if tgt not in members
                ),
            )
            comps.update(dict.fromkeys(members, cgc))
            rev_result.append(cgc)
        return list(reversed(rev_result))

    def __init__(self, calls: Mapping[MonoDefId, Iterable[MonoDefId]]):
        self._graph = nx.DiGraph()
        for mono_def_id in calls:
            finder = BoundVarFinder()
            (_, args) = mono_def_id
            # Include only concrete instantiations; the others will not be compiled.
            for arg in args:
                arg.visit(finder)
            if not finder.bound_vars:
                self._graph.add_node(mono_def_id)

        for mono_def_id, callees in calls.items():
            if mono_def_id not in self._graph.nodes:
                continue
            for tgt in callees:
                assert tgt in self._graph.nodes
                self._graph.add_edge(mono_def_id, tgt)


@dataclass(frozen=True)
class CallGraphComponent:
    """Represents a strongly connected component in the call graph."""

    members: frozenset[MonoDefId]
    callees: frozenset[tuple[MonoDefId, CallGraphComponent, MonoDefId]]
