import ast
from dataclasses import dataclass
from functools import reduce

from guppylang_internals.definition.common import DefId
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
