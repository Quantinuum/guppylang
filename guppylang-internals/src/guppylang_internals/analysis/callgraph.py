from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from types import MappingProxyType
from typing import TYPE_CHECKING

import networkx as nx

from guppylang_internals.tys.subst import BoundVarFinder

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from guppylang_internals.analysis.modifier import ConcreteCustomUse
    from guppylang_internals.engine import MonoDefId


@dataclass(frozen=True, init=False)
class ModifierAnalysisResult:
    """An immutable snapshot of program dependencies and custom modifier uses after
    modifier analysis.

    Call rows preserve order and repeated calls. Load rows record function-value
    dependencies, which do not contribute to call components or effect propagation.
    ``custom_uses_by_mono_def`` maps custom definition IDs to concrete modifier uses.
    """

    call_graph: Mapping[MonoDefId, tuple[MonoDefId, ...]]
    load_graph: Mapping[MonoDefId, frozenset[MonoDefId]]
    custom_uses_by_mono_def: Mapping[MonoDefId, ConcreteCustomUse]

    def __init__(
        self,
        call_graph: Mapping[MonoDefId, Iterable[MonoDefId]],
        load_graph: Mapping[MonoDefId, Iterable[MonoDefId]],
        custom_uses_by_mono_def: Mapping[MonoDefId, ConcreteCustomUse],
    ) -> None:
        object.__setattr__(
            self,
            "call_graph",
            MappingProxyType(
                {caller: tuple(callees) for caller, callees in call_graph.items()}
            ),
        )
        object.__setattr__(
            self,
            "load_graph",
            MappingProxyType(
                {owner: frozenset(loads) for owner, loads in load_graph.items()}
            ),
        )
        object.__setattr__(
            self,
            "custom_uses_by_mono_def",
            MappingProxyType(dict(custom_uses_by_mono_def)),
        )


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
        # Topsort puts callers first - reverse so we compute callees ready for caller.
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
        self._all_calls = calls
        self._graph = nx.DiGraph()
        for mono_def_id in calls:
            if _is_concrete(
                mono_def_id
            ):  # Only concrete functions will actually be compiled
                self._graph.add_node(mono_def_id)

        for mono_def_id, callees in calls.items():
            if mono_def_id not in self._graph.nodes:
                continue
            for tgt in callees:
                if tgt in self._graph.nodes:
                    self._graph.add_edge(mono_def_id, tgt)


def _is_concrete(mono_def_id: MonoDefId) -> bool:
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

    """Calls from functions in this component to functions outside it.
    Each tuple is (source, target component, target), with the target component being
    None if the target is not a node (was not passed to `register_call_graph_node`)."""
    external_callees: frozenset[tuple[MonoDefId, CallGraphComponent | None, MonoDefId]]
