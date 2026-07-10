import ast
from dataclasses import dataclass, field, replace
from functools import reduce
from typing import TYPE_CHECKING

import networkx as nx

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.errors.type_errors import TooManyEffectsError
from guppylang_internals.definition.function import CheckedFunctionDef
from guppylang_internals.definition.value import CallableDef
from guppylang_internals.error import GuppyTypeError
from guppylang_internals.span import Span, to_span
from guppylang_internals.tys import Effect
from guppylang_internals.tys.ty import FunctionType

if TYPE_CHECKING:
    from guppylang_internals.engine import MonoDefId


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


@dataclass
class CallGraphData:
    """Node in the call graph representing a function with its effect limit
    declaration."""

    effect_limit: EffectLimitDecl | None
    # calls to definitions, each with AST of the call
    callee_defs: list[tuple["MonoDefId", AstNode]] = field(default_factory=list)
    other_callees: list[tuple[str | None, FunctionType, AstNode]] = field(
        default_factory=list
    )


def _check_effects(
    mf: EffectLimitDecl,
    target: FunctionType,
    callee: str | None,
    node: AstNode,
) -> None:
    """Checks that a function call (AST provided) to a specified FunctionType
    respects the effect constraints in the context."""

    surplus_effects = [e for e in target.effects if e not in mf.effects]
    if surplus_effects:
        loc_node = node.func if isinstance(node, ast.Call) else node
        show_effects_allowed = (
            # We found the decorator that is the source of the effect constraint,
            # which will contain the allowed effects as an explicit argument
            None
            if isinstance(mf.decl, ast.expr)
            # Otherwise, the error message points at all decorators, which
            # may or may not list the allowed effects, so list them explicitly
            else mf.effects
        )

        callee_str = f"Callee of type {target}" if callee is None else callee

        raise GuppyTypeError(
            TooManyEffectsError(
                loc_node, callee_str, surplus_effects, mf.decl_name
            ).add_sub_diagnostic(
                TooManyEffectsError.MaxFromDecl(mf.decl, show_effects_allowed)
            )
        )


def check_compute_effects() -> None:
    """Computes the effects of functions in the program, checking that they
    respect the declared effect limits. This should be called after a call graph
    has been constructed during checking."""
    from guppylang_internals.engine import ENGINE

    # First construct a networkx DiGraph based on the call graph info for analysis.
    call_info = ENGINE.call_graph
    call_graph = nx.DiGraph(
        (caller_id, callee)
        for caller_id, info in call_info.items()
        for callee, _ in info.callee_defs
    )

    # Then compute strongly components to find cycles in the call graph. Every node
    # in a component must have the same effects.
    components = list(nx.strongly_connected_components(call_graph))
    condensed = nx.condensation(call_graph, scc=components)

    component_effects: dict[int, frozenset[Effect]] = {}
    # Start in the leaves of the condensed graph and work up to the roots, so that we
    # can compute the effects of a component based on the effects of its callees.
    for component in reversed(list(nx.topological_sort(condensed))):
        members = condensed.nodes[component]["members"]
        # Check for annotations
        annots: dict[frozenset[Effect], list[ast.expr | Span]] = {}
        for def_id in members:
            limit_decl = call_info[def_id].effect_limit
            if limit_decl is not None:
                annots.setdefault(frozenset(limit_decl.effects), []).append(
                    limit_decl.decl
                )
        annot: tuple[frozenset[Effect], ast.expr | Span] | None
        if len(annots) == 0:
            annot = None  # No function in cycle had an annotation
        else:
            try:
                ((anno, decls),) = annots.items()
                annot = (anno, decls[0])
            except:
                # TODO(callgraph): raise error for conflicting annotations
                pass

        if annot is not None:
            # Fix declared max effects for all elements of cycle
            effects, some_decl = annot
            for def_id in members:
                info: CallGraphData = call_info[def_id]
                if info.effect_limit is None:
                    limit_decl = EffectLimitDecl(
                        list(effects),
                        some_decl,
                        ENGINE.parsed[def_id].name + " (cycle)",
                    )
                    info.effect_limit = limit_decl
                else:
                    limit_decl = info.effect_limit
                # Now check calls:
                for tgt_id, ast_node in info.callee_defs:
                    tgt = ENGINE.checked[tgt_id]
                    assert isinstance(tgt, CallableDef)
                    _check_effects(limit_decl, tgt.ty, tgt.name, ast_node)
                for callee, func_ty, ast_node in info.other_callees:
                    _check_effects(limit_decl, func_ty, callee, ast_node)
        else:
            # No annotation, so compute effects based on callees
            effects = frozenset.union(
                *(component_effects[succ] for succ in condensed.successors(component))
            ).union(
                *(
                    func_ty.effects
                    for def_id in members
                    for _, func_ty, _ in call_info[def_id].other_callees
                )
            )

        component_effects[component] = effects

        # Apply inferred effects to all members of each component.
        for def_id in members:
            # Update all MonoDefIds for this DefId in ENGINE.checked.
            defn = ENGINE.checked[def_id]
            assert isinstance(defn, CheckedFunctionDef)
            if defn.ty.declared_effects is None:
                ENGINE.checked[def_id] = replace(
                    defn, ty=defn.ty.with_effects(list(effects))
                )
