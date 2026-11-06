"""Snapshots of a program's dependencies and custom modifier uses."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from types import MappingProxyType
from typing import TYPE_CHECKING

from guppylang_internals.analysis.callgraph import CallGraph

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from guppylang_internals.analysis.callgraph import CallGraphComponent
    from guppylang_internals.analysis.modifier import ConcreteCustomUse
    from guppylang_internals.engine import MonoDefId


@dataclass(frozen=True, init=False)
class ProgramGraph:
    """An immutable snapshot of program dependencies and custom modifier uses.

    Call rows preserve order and repeated calls. Load rows record function-value
    dependencies, which do not contribute to call components or effect propagation.
    Both graphs retain empty rows. The graphs and custom-use map are independent
    of the input containers.
    """

    call_graph: Mapping[MonoDefId, tuple[MonoDefId, ...]]
    load_graph: Mapping[MonoDefId, frozenset[MonoDefId]]
    custom_uses_by_mono_def: Mapping[MonoDefId, ConcreteCustomUse]

    def __init__(
        self,
        call_graph: Mapping[MonoDefId, Iterable[MonoDefId]],
        load_graph: Mapping[MonoDefId, Iterable[MonoDefId]],
        custom_uses_by_mono_def: Mapping[MonoDefId, ConcreteCustomUse] | None = None,
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
            MappingProxyType(
                dict(custom_uses_by_mono_def)
                if custom_uses_by_mono_def is not None
                else {}
            ),
        )

    @cached_property
    def condensed(self) -> tuple[CallGraphComponent, ...]:
        """Call components in topological order, with callers before callees.

        Only concrete definitions with call-graph rows are component members.
        Calls to other definitions are retained as external callees.
        """
        return tuple(CallGraph(self.call_graph).condensed)
