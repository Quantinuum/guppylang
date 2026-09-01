from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx

from guppylang_internals.tys.subst import BoundVarFinder

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from guppylang_internals.engine import MonoDefId


class CallGraph:
    graph: nx.DiGraph[MonoDefId]

    def __init__(self, calls: Mapping[MonoDefId, Iterable[MonoDefId]]):
        self.graph = nx.DiGraph()
        for mono_def_id in calls:
            finder = BoundVarFinder()
            (_, args) = mono_def_id
            # Include only concrete instantiations; the others will not be compiled.
            for arg in args:
                arg.visit(finder)
            if not finder.bound_vars:
                self.graph.add_node(mono_def_id)

        for mono_def_id, callees in calls.items():
            if mono_def_id not in self.graph.nodes:
                continue
            for tgt in callees:
                assert tgt in self.graph.nodes
                self.graph.add_edge(mono_def_id, tgt)
