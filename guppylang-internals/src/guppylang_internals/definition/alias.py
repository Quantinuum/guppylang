import ast
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import ClassVar

from guppylang_internals.ast_util import AstNode, get_file
from guppylang_internals.checker.core import Globals
from guppylang_internals.definition.common import (
    CheckableDef,
    CompiledDef,
    DefId,
    ParsableDef,
)
from guppylang_internals.definition.parameter import ParamDef, RawConstVarDef
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.diagnostic import Error, Note
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.error import GuppyError, InternalGuppyError
from guppylang_internals.span import SourceMap, to_span
from guppylang_internals.tys.arg import Argument
from guppylang_internals.tys.param import Parameter, check_all_args
from guppylang_internals.tys.parsing import TypeParsingCtx, type_from_ast
from guppylang_internals.tys.subst import Instantiator
from guppylang_internals.tys.ty import Type

_active_alias_checks: ContextVar[tuple["ParsedTypeAliasDef", ...]] = ContextVar(
    "_active_alias_checks", default=()
)


@dataclass(frozen=True)
class RecursiveTypeAliasError(Error):
    title: ClassVar[str] = "Recursive type alias"
    cycle: tuple[str, ...]

    @property
    def rendered_span_label(self) -> str:
        if len(self.cycle) == 2 and self.cycle[0] == self.cycle[1]:
            return f"Type alias `{self.cycle[0]}` expands to itself"
        return "Type alias cycle detected:\n" + " -> ".join(
            f"`{alias}`" for alias in self.cycle
        )

    @dataclass(frozen=True)
    class AliasNote(Note):
        alias_name: str
        defn_id: DefId
        span_label: ClassVar[str] = "`{alias_name}` defined here"


@dataclass(frozen=True)
class RawTypeAliasDef(TypeDef, ParsableDef):
    """A raw type alias definition that has not been parsed yet."""

    type_ast: ast.expr
    explicit_params: Sequence[ParamDef] | None = None
    params: None = field(default=None, init=False)
    description: str = field(default="type alias", init=False)

    def parse(self, globals: Globals, sources: SourceMap) -> "ParsedTypeAliasDef":
        return ParsedTypeAliasDef(
            self.id,
            self.name,
            self.defined_at,
            self.explicit_params,
            self.type_ast,
        )

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        raise InternalGuppyError("Tried to instantiate raw type alias definition")


def _resolve_param(defn: ParamDef, idx: int, globals: Globals) -> Parameter:
    """Convert a parameter definition to a positional :class:`Parameter`.

    ``const_var`` definitions arrive unparsed (their type is still a raw AST), so we
    parse them here, where the ``globals`` needed to resolve the type are available.
    """
    if isinstance(defn, RawConstVarDef):
        defn = defn.parse(globals, DEF_STORE.sources)
    return defn.to_param(idx)


@dataclass(frozen=True)
class ParsedTypeAliasDef(TypeDef, CheckableDef):
    """A type alias definition whose target type has not been checked yet."""

    param_defs: Sequence[ParamDef] | None
    type_ast: ast.expr
    params: None = field(default=None, init=False)
    description: str = field(default="type alias", init=False)

    def check(self, globals: Globals) -> "CheckedTypeAliasDef":
        if self.param_defs is not None:
            # Explicit params: resolve each definition to a parameter (parsing
            # `const_var` types now that globals are available) and pre-load them
            # into the context so that variables in the body bind to these params
            # in order.
            resolved = [
                _resolve_param(p, i, globals) for i, p in enumerate(self.param_defs)
            ]
            ctx = TypeParsingCtx(
                globals, param_var_mapping={p.name: p for p in resolved}
            )
            check_not_recursive(self, ctx)
            ty = type_from_ast(self.type_ast, ctx)
            params = tuple(resolved)
        else:
            # Implicit: collect free type vars from the body in order of appearance.
            ctx = TypeParsingCtx(globals, allow_free_vars=True)
            check_not_recursive(self, ctx)
            ty = type_from_ast(self.type_ast, ctx)
            params = tuple(ctx.param_var_mapping.values())
        return CheckedTypeAliasDef(
            self.id,
            self.name,
            self.defined_at,
            params,
            ty,
        )

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        globals = Globals(DEF_STORE.frames[self.id])
        checked_def = self.check(globals)
        return checked_def.check_instantiate(args, loc)


@dataclass(frozen=True)
class CheckedTypeAliasDef(TypeDef, CompiledDef):
    """A fully checked type alias definition."""

    params: Sequence[Parameter]
    ty: Type
    description: str = field(default="type alias", init=False)

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        check_all_args(self.params, args, self.name, loc)
        return self.ty.transform(Instantiator(args))


@contextmanager
def _patched_check_instantiate(
    defn: ParsedTypeAliasDef,
    replacement: Callable[[Sequence[Argument], AstNode | None], Type],
) -> Iterator[None]:
    """Temporarily override `check_instantiate` for recursive-alias detection."""
    object.__setattr__(defn, "check_instantiate", replacement)
    try:
        yield
    finally:
        # Remove the instance attribute so method resolution falls back to the
        # class descriptor, restoring the original behaviour cleanly.
        object.__delattr__(defn, "check_instantiate")


def check_not_recursive(defn: ParsedTypeAliasDef, ctx: TypeParsingCtx) -> None:
    """Throws a user error if the given type alias is recursive.

    We do not have a separate alias-expansion pass, so we detect recursion by
    temporarily swapping out this alias's `check_instantiate` method while parsing its
    target type. If parsing the alias body reaches this same alias again, the patched
    method fires and turns that recursive re-entry into a user-facing cycle diagnostic.

    All cycle notes are attached at once inside `dummy_check_instantiate` so that only
    aliases that are actually part of the cycle receive notes (not outer aliases that
    merely lead to a cycle).
    """
    token = _active_alias_checks.set((*_active_alias_checks.get(), defn))

    def dummy_check_instantiate(
        args: Sequence[Argument],
        loc: AstNode | None = None,
    ) -> Type:
        active = _active_alias_checks.get()
        start = next(
            i for i, active_defn in enumerate(active) if active_defn.id == defn.id
        )
        cycle_defs = (*active[start:], defn)
        cycle = tuple(d.name for d in cycle_defs)
        err = RecursiveTypeAliasError(loc, cycle)
        _add_alias_notes_for_cycle(err, cycle_defs)
        raise GuppyError(err)

    try:
        with _patched_check_instantiate(defn, dummy_check_instantiate):
            type_from_ast(defn.type_ast, ctx)
    finally:
        _active_alias_checks.reset(token)


def _add_alias_notes_for_cycle(
    err: RecursiveTypeAliasError,
    cycle_defs: tuple["ParsedTypeAliasDef", ...],
) -> None:
    """Attach notes for every alias in the cycle in a single pass.

    `cycle_defs` is `(A, B, ..., A)` where the first and last element are identical.
    We skip self-cycles (only one unique member) since the span label on the error
    already says the alias "expands to itself".

    Notes are only emitted when the alias definition has a valid, same-file span — i.e.
    when the AST node was annotated with file information by `_parse_expr_string`.
    Cross-file or un-annotated spans are silently skipped; the cycle chain in the main
    error's span label is still fully informative on its own.
    """
    unique_defs = cycle_defs[:-1]  # drop the repeated last element
    if len(unique_defs) <= 1:
        return

    # File the main error is anchored to. `add_sub_diagnostic` requires every note to
    # share this file, and `to_span` requires the span to carry a file, so definitions
    # without a matching file annotation are skipped below.
    err_file = to_span(err.span).file if err.span is not None else None

    # The last element of `unique_defs` is the alias whose definition the error span
    # already underlines — skip it to avoid a redundant note on the same line. Use
    # DefId for deduplication so that aliases with identical names don't collide.
    seen_ids: set[DefId] = set()
    for defn in unique_defs[:-1]:
        if defn.id in seen_ids or defn.defined_at is None:
            continue
        note_file = get_file(defn.defined_at)
        if note_file is None or note_file != err_file:
            continue
        seen_ids.add(defn.id)
        err.add_sub_diagnostic(
            RecursiveTypeAliasError.AliasNote(defn.defined_at, defn.name, defn.id)
        )
