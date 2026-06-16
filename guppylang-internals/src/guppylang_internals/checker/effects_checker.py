import ast
from dataclasses import dataclass, replace
from functools import reduce

import networkx as nx

from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.value import CallableDef
from guppylang_internals.span import Span, to_span
from guppylang_internals.tys import Effect
from guppylang_internals.tys.ty import FunctionType


@dataclass(frozen=True)
class CallGraphNode:
    """Node in the call graph representing a function with its effect limit
    declaration."""

    def_id: DefId
    effect_limit: "EffectLimitDecl | None"

    def __hash__(self) -> int:
        return hash(self.def_id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CallGraphNode):
            return self.def_id == other.def_id
        # Allow look ups by DefId for convenience.
        return self.def_id == other


@dataclass(frozen=True)
class EffectLimitDecl:
    """Records a declaration limiting the effects that may be used in a Context"""

    effects: list[Effect]
    decl: ast.expr | Span
    decl_name: str

    @classmethod
    def for_def(
        cls, ty: FunctionType, func_def: ast.FunctionDef
    ) -> "EffectLimitDecl | None":
        if ty.declared_effects is None:
            return None
        if (deco := _find_guppy_decorator(func_def.decorator_list)) is not None:
            decl = deco
        else:
            # Could not identify decorator, so include all in context; union with
            # returns will include name etc. inbetween but avoid the function body.
            elems = func_def.decorator_list
            if func_def.returns is not None:
                elems += [func_def.returns]

            def union(s1: Span, s2: Span) -> Span:
                r = s1 | s2
                assert r is not None  # Function def should not cross file boundary
                return r

            decl = reduce(union, (to_span(e) for e in elems))

        return EffectLimitDecl(
            ty.declared_effects,
            decl,
            func_def.name,
        )


def _find_guppy_decorator(decorators: list[ast.expr]) -> ast.expr | None:
    for d in decorators:
        if (
            isinstance(d, ast.Call)
            and isinstance(d.func, ast.Name)
            and d.func.id == "guppy"
        ):
            return d
        if isinstance(d, ast.Name) and d.id == "guppy":
            return d
    return None


def _get_func_ty(def_id: DefId) -> FunctionType | None:
    # TODO(callgraph): How to get the correct Inst here?
    from guppylang_internals.engine import ENGINE
    defn = ENGINE.get_checked(def_id, ())
    if isinstance(defn, CallableDef):
        return defn.ty
    return None


def _check_effects(call_info: dict[CallGraphNode, list[DefId]]) -> None:

    def callee_effects(def_id: DefId) -> list[Effect]:
        ty = _get_func_ty(def_id)
        return ty.effects if ty is not None else [Effect.ANY]

    for caller, callees in call_info.items():
        mf = caller.effect_limit
        if mf is None:
            continue

        for callee in callees:
            surplus_effects = [e for e in callee_effects(callee) if e not in mf.effects]
            if not surplus_effects:
                continue

            # TODO(callgraph): How to best raise error here without AstNode?


def compute_effects() -> None:
    """Computes the effects of functions in the program, checking that they
    respect the declared effect limits. This should be called after a call graph
    has been constructed during checking."""
    from guppylang_internals.engine import ENGINE
    # First construct a networkx DiGraph based on the call graph info for analysis.
    call_info = ENGINE.call_graph
    call_graph = nx.DiGraph(
        (caller.def_id, callee)
        for caller, callees in call_info.items()
        for callee in callees
    )

    # Then compute strongly components to find cycles in the call graph. Every node
    # in a component must have the same effects.
    components = list(nx.strongly_connected_components(call_graph))
    condensed = nx.condensation(call_graph, scc=components)

    component_effects: dict[int, set[Effect]] = {}
    # Start in the leaves of the condensed graph and work up to the roots, so that we
    # can compute the effects of a component based on the effects of its callees.
    for component in reversed(list(nx.topological_sort(condensed))):
        members = condensed.nodes[component]["members"]
        effects: set[Effect] = set()

        # Add explicit annotations, we know these must be valid as we check annotations
        # during checking.
        for def_id in members:
            ty = _get_func_ty(def_id)

            if ty is not None and ty.declared_effects is not None:
                effects.update(ty.declared_effects)

        # Calls outside of the component contribute their already-inferred effects.
        for succ in condensed.successors(component):
            effects.update(component_effects[succ])

        component_effects[component] = effects

    # Apply inferred effects to all members of each component.
    for component in condensed.nodes:
        members = condensed.nodes[component]["members"]
        inferred = list(component_effects[component])
        for def_id in members:
            ty = _get_func_ty(def_id)
            defn = ENGINE.get_checked(def_id, ())
            # TODO(callgraph): Clean up these checks.
            if ty is None or defn is None:
                continue
            if ty.declared_effects is not None or not isinstance(defn, CallableDef):
                # Already has an explicit annotation, so we should not update it.
                continue
            # TODO(callgraph): How to get correct MonoDefId here?
            ENGINE.checked[(def_id, ())] = replace(
                defn, ty=ty.with_effects(inferred)
            )

    # Check effects again, doing essentially the same as expr_checker._check_effects but
    # on the call graph with inferred effects rather than on individual calls.
    _check_effects(call_info)
