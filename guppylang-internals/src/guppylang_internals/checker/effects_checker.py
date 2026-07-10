from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import networkx as nx

from guppylang_internals.error import InternalGuppyError
from guppylang_internals.tys import Effect

if TYPE_CHECKING:
    from guppylang_internals.engine import MonoDefId


@dataclass
class CallGraphData:
    """Node in the call graph representing a function with its effect limit
    declaration."""

    # calls to definitions, each with AST of the call
    callee_defs: list["MonoDefId"] = field(default_factory=list)
    other_callee_effects: list[Effect] = field(default_factory=list)


def compute_effects() -> Mapping["MonoDefId", frozenset[Effect]]:
    """Computes the effects of functions in the program, checking that they
    respect the declared effect limits. This should be called after a call graph
    has been constructed during checking."""
    from guppylang_internals.engine import ENGINE

    # First construct a networkx DiGraph based on the call graph info for analysis.
    call_graph: nx.DiGraph[MonoDefId] = nx.DiGraph()
    call_graph.add_nodes_from(ENGINE.call_graph.keys())
    for mono_def_id, data in ENGINE.call_graph.items():
        effects = set(data.other_callee_effects)
        for tgt in data.callee_defs:
            if tgt in call_graph:
                call_graph.add_edge(mono_def_id, tgt)
            else:
                # ALAN TODO we should probably pass in a CallableDef, or similar,
                # rather than DefId, and give that a get-effects method that returns
                # either a set of effects or a MonoDefId "callgraph node" to compute.
                from guppylang_internals.definition.declaration import (
                    ParsedFunctionDecl,
                )
                from guppylang_internals.definition.function import ParsedFunctionDef
                from guppylang_internals.definition.pytket_circuits import (
                    ParsedPytketDef,
                )
                from guppylang_internals.definition.traced import RawTracedFunctionDef

                (def_id, _inst) = tgt
                match ENGINE.get_parsed(def_id):
                    case RawTracedFunctionDef():
                        # ALAN effect info not available yet...would be good to use
                        # CompiledTracedFunctionDef.call_effects
                        effects.update([Effect.ANY])
                    case ParsedFunctionDef(ty=ty):
                        assert len(ty.params) > 0
                        # Comptime params - ALAN are instantiations recorded?
                        # In principle it's same as previous and we have to:
                        effects.update([Effect.ANY])
                    case ParsedFunctionDecl():
                        # No effect annotations on decls yet
                        effects.update([Effect.ANY])
                    case ParsedPytketDef():
                        pass  # Pure!
                    case x:
                        raise InternalGuppyError(f"Unknown function defn {type(x)}")
        call_graph.nodes[mono_def_id]["effects"] = effects

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
    for k, v in ENGINE.checked.items():
        from guppylang_internals.definition.custom import CustomFunctionDef
        from guppylang_internals.definition.declaration import ParsedFunctionDecl
        from guppylang_internals.definition.traced import TracedFunctionDef
        from guppylang_internals.definition.value import CallableDef

        if isinstance(v, CallableDef) and not isinstance(
            v, (CustomFunctionDef, TracedFunctionDef, ParsedFunctionDecl)
        ):
            assert k in ENGINE.call_graph
            assert k in mapping
    return mapping
