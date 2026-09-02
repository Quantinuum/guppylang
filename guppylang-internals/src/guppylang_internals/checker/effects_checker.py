from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

import networkx as nx

# from matplotlib import pyplot as plt
from guppylang_internals.tys import Effect
from guppylang_internals.tys.const import Const, ConstValue
from guppylang_internals.tys.subst import is_concrete_inst
from guppylang_internals.tys.ty import (
    CALL_CONTROLLED_METHOD,
    CALL_CTRL_DAGGERED_METHOD,
    CALL_DAGGERED_METHOD,
)

if TYPE_CHECKING:
    from guppylang_internals.engine import MonoDefId


class CustomModifierKind(Enum):
    """Kinds of custom implementations supported by ``@guppy.unitary``."""

    DAGGERED = CALL_DAGGERED_METHOD
    CONTROLLED = CALL_CONTROLLED_METHOD
    CTRL_DAGGERED = CALL_CTRL_DAGGERED_METHOD

    @property
    def takes_controls(self) -> bool:
        """Whether the implementation has a control-count parameter."""
        return self in {
            CustomModifierKind.CONTROLLED,
            CustomModifierKind.CTRL_DAGGERED,
        }


@dataclass(frozen=True)
class ModifierContext:
    """Dagger and control modifiers active at a call site."""

    daggered: bool = False
    control_sizes: tuple[int | Const, ...] = ()

    def compose(self, inner: "ModifierContext") -> "ModifierContext":
        """
        Return a new CallModifiers instance by composing modifiers self with inner.
        """
        return ModifierContext(
            daggered=self.daggered ^ inner.daggered,
            control_sizes=(*self.control_sizes, *inner.control_sizes),
        )

    def concrete_control_count(self) -> int:
        """Returns the total number of controls in a concrete context."""
        total = 0
        for size in self.control_sizes:
            match size:
                case int() as value:
                    total += value
                case ConstValue(value=int() as value):
                    total += value
                case _:
                    raise ValueError("Control count is not concrete")
        return total

    def kind_required(self) -> CustomModifierKind | None:
        """Returns the kind of custom modifier required by this context, if any."""
        if self.daggered and len(self.control_sizes) > 0:
            return CustomModifierKind.CTRL_DAGGERED
        if self.daggered:
            return CustomModifierKind.DAGGERED
        if len(self.control_sizes) > 0:
            return CustomModifierKind.CONTROLLED
        return None


NO_CALL_MODIFIERS = ModifierContext()


@dataclass
class CallGraphData:
    """Node in the call graph representing a function with its effect limit
    declaration."""

    callee_defs: list["MonoDefId"] = field(default_factory=list)
    other_callee_effects: list[Effect] = field(default_factory=list)


def compute_effects(
    func_data: Mapping["MonoDefId", CallGraphData],
) -> Mapping["MonoDefId", frozenset[Effect]]:
    """Computes the effects of functions in the program, checking that they
    respect the declared effect limits. This should be called after a call graph
    has been constructed during checking."""

    # First construct a networkx DiGraph based on the call graph info for analysis.
    call_graph: nx.DiGraph[MonoDefId] = nx.DiGraph()
    for mono_def_id in func_data:
        (_, args) = mono_def_id
        # Include only real/concrete instantiations, the others will not be compiled.
        if is_concrete_inst(args):
            call_graph.add_node(mono_def_id)

    for mono_def_id, data in func_data.items():
        if mono_def_id not in call_graph.nodes:
            continue
        effects = set(data.other_callee_effects)
        for tgt in data.callee_defs:
            assert tgt in call_graph.nodes
            call_graph.add_edge(mono_def_id, tgt)
        call_graph.nodes[mono_def_id]["effects"] = effects

    nx.draw(call_graph, with_labels=True)
    # plt.gca().margins(x=4)
    # # plt.savefig("call_graph.png")
    # plt.show()
    # plt.close()

    # Then compute strongly components to find cycles in the call graph. Every node
    # in a component must have the same effects.
    components = list(nx.strongly_connected_components(call_graph))
    condensed = nx.condensation(call_graph, scc=components)

    # These two store the same info but for access during SCC traversal
    # and for compilation later
    component_effects: dict[int, frozenset[Effect]] = {}
    mapping: dict[MonoDefId, frozenset[Effect]] = {}

    # Start in the leaves of the condensed graph and work up to the roots, so that we
    # can compute the effects of a component based on the effects of its callees.
    for component in reversed(list(nx.topological_sort(condensed))):
        members = condensed.nodes[component]["members"]
        effects = set.union(
            *(call_graph.nodes[mono_def_id]["effects"] for mono_def_id in members)
        )
        for succ in condensed.successors(component):
            effects.update(component_effects[succ])

        fx = frozenset(effects)
        component_effects[component] = fx

        # Apply inferred effects to all members of each component.
        for def_id in members:
            mapping[def_id] = fx

    return mapping
