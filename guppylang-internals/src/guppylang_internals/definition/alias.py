import ast
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import ClassVar

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.core import Globals
from guppylang_internals.definition.common import (
    CheckableDef,
    CompiledDef,
    ParsableDef,
)
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.diagnostic import Error, Help, Note
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.error import GuppyError, InternalGuppyError
from guppylang_internals.span import SourceMap
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
        span_label: ClassVar[str] = "Alias `{alias_name}` is part of this cycle"

    @dataclass(frozen=True)
    class Fix(Help):
        message: ClassVar[str] = (
            "Type aliases must eventually resolve to a non-alias type. Break the "
            "cycle by inlining one alias or introducing a struct or enum wrapper."
        )

    def __post_init__(self) -> None:
        self.add_sub_diagnostic(RecursiveTypeAliasError.Fix(None))


@dataclass(frozen=True)
class RawTypeAliasDef(TypeDef, ParsableDef):
    """A raw type alias definition that has not been parsed yet."""

    type_ast: ast.expr
    params: None = field(default=None, init=False)
    description: str = field(default="type alias", init=False)

    def parse(self, globals: Globals, sources: SourceMap) -> "ParsedTypeAliasDef":
        return ParsedTypeAliasDef(
            self.id,
            self.name,
            self.defined_at,
            None,
            self.type_ast,
        )

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        raise InternalGuppyError("Tried to instantiate raw type alias definition")


@dataclass(frozen=True)
class ParsedTypeAliasDef(TypeDef, CheckableDef):
    """A type alias definition whose target type has not been checked yet."""

    params: Sequence[Parameter] | None
    type_ast: ast.expr
    description: str = field(default="type alias", init=False)

    def check(self, globals: Globals) -> "CheckedTypeAliasDef":
        recursion_ctx = TypeParsingCtx(globals, allow_free_vars=True)
        check_not_recursive(self, recursion_ctx)

        ctx = TypeParsingCtx(globals, allow_free_vars=True)
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
    original = defn.check_instantiate
    object.__setattr__(defn, "check_instantiate", replacement)
    try:
        yield
    finally:
        object.__setattr__(defn, "check_instantiate", original)


def check_not_recursive(defn: ParsedTypeAliasDef, ctx: TypeParsingCtx) -> None:
    """Throws a user error if the given type alias is recursive.

    We do not have a separate alias-expansion pass, so we detect recursion by
    temporarily swapping out this alias's `check_instantiate` method while parsing its
    target type. If parsing the alias body reaches this same alias again, the patched
    method fires and turns that recursive re-entry into a user-facing cycle diagnostic.
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
        cycle = tuple(
            _alias_name(active_defn, ctx.globals) for active_defn in cycle_defs
        )
        err = RecursiveTypeAliasError(loc, cycle)
        _add_alias_note(err, defn, ctx.globals)
        raise GuppyError(err)

    try:
        with _patched_check_instantiate(defn, dummy_check_instantiate):
            type_from_ast(defn.type_ast, ctx)
    except GuppyError as err:
        if isinstance(err.error, RecursiveTypeAliasError):
            _add_alias_note(err.error, defn, ctx.globals)
        raise
    finally:
        _active_alias_checks.reset(token)


def _add_alias_note(
    err: RecursiveTypeAliasError, defn: ParsedTypeAliasDef, globals: Globals
) -> None:
    alias_name = _alias_name(defn, globals)
    # The same recursive error is re-raised while unwinding through each alias in the
    # cycle, so avoid attaching the same note more than once.
    if any(
        isinstance(child, RecursiveTypeAliasError.AliasNote)
        and child.alias_name == alias_name
        for child in err.children
    ):
        return
    err.add_sub_diagnostic(
        RecursiveTypeAliasError.AliasNote(defn.defined_at, alias_name)
    )


def _alias_name(defn: ParsedTypeAliasDef, globals: Globals) -> str:
    from guppylang.defs import GuppyDefinition

    for namespace in (globals.f_locals, globals.f_globals):
        for name, value in namespace.items():
            if isinstance(value, GuppyDefinition) and value.id == defn.id:
                return name
    return defn.name
