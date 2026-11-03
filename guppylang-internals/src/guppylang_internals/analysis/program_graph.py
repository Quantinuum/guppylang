"""Snapshots of a program's call and function-load dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from types import MappingProxyType
from typing import TYPE_CHECKING

from guppylang_internals.analysis.callgraph import CallGraph

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from guppylang_internals.analysis.callgraph import CallGraphComponent
    from guppylang_internals.engine import MonoDefId


@dataclass(frozen=True, init=False)
class ProgramGraph:
    """An immutable snapshot of call and function-load graphs.

    Call rows preserve order and repeated calls. Load rows record function-value
    dependencies, which do not contribute to call components or effect propagation.
    Both graphs retain empty rows and are independent of the input containers.
    """

    call_graph: Mapping[MonoDefId, tuple[MonoDefId, ...]]
    load_graph: Mapping[MonoDefId, frozenset[MonoDefId]]

    def __init__(
        self,
        call_graph: Mapping[MonoDefId, Iterable[MonoDefId]],
        load_graph: Mapping[MonoDefId, Iterable[MonoDefId]],
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

    @cached_property
    def condensed(self) -> tuple[CallGraphComponent, ...]:
        """Call components in topological order, with callers before callees.

        Only concrete definitions with call-graph rows are component members.
        Calls to other definitions are retained as external callees.
        """
        return tuple(CallGraph(self.call_graph).condensed)
