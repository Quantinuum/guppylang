import ast
from dataclasses import dataclass, replace
from functools import reduce
from typing import TypeAlias

import networkx as nx

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.core import Context
from guppylang_internals.checker.errors.type_errors import TooManyEffectsError
from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.value import CallableDef
from guppylang_internals.error import GuppyTypeError
from guppylang_internals.span import Span, to_span
from guppylang_internals.tys import Effect
from guppylang_internals.tys.subst import Inst
from guppylang_internals.tys.ty import FunctionType

# A function definition; a protocol definition and the name of the function within it;
# or a string for error messages if there is no definition
CalleeId: TypeAlias = DefId | tuple[DefId, str] | str


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


CallableDefns = list[tuple[Inst, CallableDef]]


def _precompute_callables() -> dict[DefId, CallableDefns]:
    """In order to retrieve all definitions corresponding to a DefId after
    monomorphisation, we iterate over all checked definitions once at the start.

    # TODO(callgraph): Is this a valid assumption?
    All instantiations of the same DefId should have the same effects.
    """
    from guppylang_internals.engine import ENGINE

    result: dict[DefId, list[tuple[Inst, CallableDef]]] = {}
    for (def_id, inst), defn in ENGINE.checked.items():
        if isinstance(defn, CallableDef):
            if def_id not in result:
                result[def_id] = []
            result[def_id].append((inst, defn))
    return result


def _get_effects(
    def_id: DefId, callables: dict[DefId, CallableDefns]
) -> list[Effect] | None:
    entries = callables.get(def_id)
    if entries:
        # All instantiations of the same DefId should have the same effects so we can
        # just return the first one.
        return entries[0][1].ty.declared_effects

    return None


def _check_effects(
    ctx: Context,
    target: FunctionType,
    callee_id: CalleeId | None,
    current_caller: CallGraphNode,
    node: AstNode,
) -> None:
    """Checks that a function call (AST provided) to a specified FunctionType
    respects the effect constraints in the context."""

    if (mf := current_caller.effect_limit) is None:
        return  # ALAN definitely wrong here
    surplus_effects = [e for e in target.effects if e not in mf.effects]
    if surplus_effects:
        loc_node = node.func if isinstance(node, ast.Call) else node
        callee: str | FunctionType = (
            target
            if callee_id is None
            else ctx.globals[callee_id].name
            if isinstance(callee_id, DefId)
            else f"Function {callee_id[1]} in protocol {ctx.globals[callee_id[0]].name}"
            if isinstance(callee_id, tuple)
            else callee_id
        )
        show_effects_allowed = (
            # We found the decorator that is the source of the effect constraint,
            # which will contain the allowed effects as an explicit argument
            None
            if isinstance(mf.decl, ast.expr)
            # Otherwise, the error message points at all decorators, which
            # may or may not list the allowed effects, so list them explicitly
            else mf.effects
        )

        raise GuppyTypeError(
            TooManyEffectsError(
                loc_node, callee, surplus_effects, mf.decl_name
            ).add_sub_diagnostic(
                TooManyEffectsError.MaxFromDecl(mf.decl, show_effects_allowed)
            )
        )


def _check_effects_callgraph(
    call_info: dict[CallGraphNode, list[DefId]], callables: dict[DefId, CallableDefns]
) -> None:
    for caller, callees in call_info.items():
        mf = caller.effect_limit
        if mf is None:
            continue

        for callee in callees:
            callee_effects = _get_effects(callee, callables)
            if callee_effects is None:
                continue
            surplus_effects = [e for e in callee_effects if e not in mf.effects]
            if not surplus_effects:
                continue

            # TODO(callgraph): How to best raise error here without AstNode?


def compute_effects() -> None:
    """Computes the effects of functions in the program, checking that they
    respect the declared effect limits. This should be called after a call graph
    has been constructed during checking."""
    from guppylang_internals.engine import ENGINE

    # Pre-compute mapping from DefId to all callable definitions to deal with
    # monomorphisation.
    callables = _precompute_callables()

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

        # Add explicit annotations.
        for def_id in members:
            defn_effects = _get_effects(def_id, callables)
            if defn_effects is not None:
                effects.update(defn_effects)

        # Calls outside of the component contribute their already-inferred effects.
        for succ in condensed.successors(component):
            effects.update(component_effects[succ])

        component_effects[component] = effects

    # Apply inferred effects to all members of each component.
    for component in condensed.nodes:
        members = condensed.nodes[component]["members"]
        inferred = list(component_effects[component])
        for def_id in members:
            existing_effects = _get_effects(def_id, callables)
            if existing_effects is not None:
                # Already has an explicit annotation.
                continue
            # Update all MonoDefIds for this DefId in ENGINE.checked.
            if def_id in callables:
                for inst, defn in callables[def_id]:
                    # TODO(callgraph): defn seems to be `CompilableDef`?
                    ENGINE.checked[(def_id, inst)] = replace(
                        defn, ty=defn.ty.with_effects(inferred)
                    )

    # Traverse the call graph to check that both explicit and inferred effects respect
    # the declared effect limits.
    _check_effects_callgraph(call_info, callables)
