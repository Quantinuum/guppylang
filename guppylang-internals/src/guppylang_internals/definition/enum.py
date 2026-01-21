import ast
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.core import Globals
from guppylang_internals.checker.errors.generic import UnsupportedError
from guppylang_internals.definition.common import CheckableDef
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.diagnostic import Error
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.error import GuppyError
from guppylang_internals.tys.arg import Argument
from guppylang_internals.tys.param import Parameter, check_all_args
from guppylang_internals.tys.parsing import TypeParsingCtx, type_from_ast
from guppylang_internals.tys.ty import EnumType, Type

# ============================================================================
# Variant Classes
# ============================================================================


@dataclass(frozen=True)
class UncheckedEnumVariant:
    """A variant on an enum whose payload types have not been checked yet."""

    name: str
    payload_types: list[ast.expr]


@dataclass(frozen=True)
class EnumVariant:
    """A variant on an enum with checked payload types."""

    name: str
    payload_types: list[Type]


# ============================================================================
# Error Classes (Minimal)
# ============================================================================


@dataclass(frozen=True)
class DuplicateVariantError(Error):
    """Error raised when an enum has duplicate variant names."""

    title: ClassVar[str] = "Duplicate variant"
    span_label: ClassVar[str] = "Variant `{variant_name}` is already defined"
    variant_name: str


# ============================================================================
# Definition Classes (Minimal - No Raw, just Parsed and Checked)
# ============================================================================


@dataclass(frozen=True)
class ParsedEnumDef(TypeDef, CheckableDef):
    """An enum definition whose variant types have not been checked yet.

    This is a minimal implementation without full parsing support.
    For PR 1, you can create these directly for testing.
    """

    defined_at: ast.ClassDef
    params: Sequence[Parameter]
    variants: Sequence[UncheckedEnumVariant]

    def check(self, globals: Globals) -> "CheckedEnumDef":
        """Checks that all enum variant payload types are valid.

        Args:
            globals: The global definitions available in this scope

        Returns:
            A CheckedEnumDef with fully resolved types

        Raises:
            GuppyError: If any variant has invalid types or the enum is recursive
        """
        param_var_mapping = {p.name: p for p in self.params}
        ctx = TypeParsingCtx(globals, param_var_mapping)

        # Before checking the variants, make sure that this definition is not recursive,
        # otherwise the code below would not terminate.
        # TODO: This is not ideal (see todo in `check_instantiate`)
        check_not_recursive(self, ctx)

        # Parse and check all variant payload types
        variants = [
            EnumVariant(
                v.name,
                [type_from_ast(payload_ast, ctx) for payload_ast in v.payload_types],
            )
            for v in self.variants
        ]

        return CheckedEnumDef(
            self.id, self.name, self.defined_at, self.params, variants
        )

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        """Checks if the enum can be instantiated with the given arguments."""
        check_all_args(self.params, args, self.name, loc)
        globals = Globals(DEF_STORE.frames[self.id])
        # TODO: This is quite bad: If we have a cyclic definition this will not
        #  terminate, so we have to check for cycles in every call to `check`. The
        #  proper way to deal with this is changing `EnumType` such that it only
        #  takes a `DefId` instead of a `CheckedEnumDef`. But this will be a bigger
        #  refactor... (See PR 4)
        checked_def = self.check(globals)
        return EnumType(args, checked_def)


@dataclass(frozen=True)
class CheckedEnumDef(TypeDef):
    """An enum definition that has been fully checked.

    All variant payload types have been resolved and validated.
    """

    defined_at: ast.ClassDef
    params: Sequence[Parameter]
    variants: Sequence[EnumVariant]

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        """Checks if the enum can be instantiated with the given arguments."""
        check_all_args(self.params, args, self.name, loc)
        return EnumType(args, self)


# ============================================================================
# Recursion Checking
# ============================================================================


def check_not_recursive(defn: ParsedEnumDef, ctx: TypeParsingCtx) -> None:
    """Throws a user error if the given enum definition is recursive.

    This function temporarily replaces the enum's check_instantiate method with
    a dummy that raises an error. Then it attempts to parse all variant payload
    types. If any variant references the enum being defined, the dummy method
    will be called, catching the recursion.

    Args:
        defn: The parsed enum definition to check for recursion
        ctx: The type parsing context containing available types

    Raises:
        GuppyError: If the enum is directly or mutually recursive

    Note:
        This is a TEMPORARY hacky implementation (see PR 4 for the proper solution).
    """
    # TODO: The implementation below hijacks the type parsing logic to detect recursive
    #  enums. This is not great since it repeats the work done during checking. We can
    #  get rid of this after resolving the todo in `ParsedEnumDef.check_instantiate()`
    #  This will be fixed in PR 4 with DefId refactoring.

    def dummy_check_instantiate(
        args: Sequence[Argument],
        loc: AstNode | None = None,
    ) -> Type:
        """Dummy method that raises an error if called during type parsing."""
        raise GuppyError(UnsupportedError(loc, "Recursive enums"))

    # Save the original check_instantiate method
    original = defn.check_instantiate

    # Temporarily replace it with the dummy that raises on recursion
    object.__setattr__(defn, "check_instantiate", dummy_check_instantiate)

    try:
        # Attempt to parse all variant payload types
        for variant in defn.variants:
            for payload_type_ast in variant.payload_types:
                type_from_ast(payload_type_ast, ctx)
    finally:
        # Always restore the original method
        object.__setattr__(defn, "check_instantiate", original)
