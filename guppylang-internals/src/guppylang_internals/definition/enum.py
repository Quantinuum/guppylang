import ast
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from guppylang.defs import GuppyDefinition
from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.core import Globals
from guppylang_internals.checker.errors.generic import UnexpectedError, UnsupportedError
from guppylang_internals.definition.common import CheckableDef, ParsableDef, CompiledDef
from guppylang_internals.definition.custom import CustomFunctionDef
from guppylang_internals.definition.util import extract_generic_params, parse_py_class
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.diagnostic import Error, Help
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.error import GuppyError, InternalGuppyError
from guppylang_internals.span import SourceMap
from guppylang_internals.tys.arg import Argument
from guppylang_internals.tys.param import Parameter, check_all_args
from guppylang_internals.tys.parsing import TypeParsingCtx, type_from_ast
from guppylang_internals.tys.ty import EnumType, Type


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


@dataclass(frozen=True)
class DuplicateVariantError(Error):
    """Error raised when an enum has duplicate variant names."""

    title: ClassVar[str] = "Duplicate variant"
    span_label: ClassVar[str] = "Variant `{variant_name}` is already defined"
    variant_name: str


@dataclass(frozen=True)
class NonGuppyMethodError(Error):
    """Error raised when an enum method is not a Guppy function."""

    title: ClassVar[str] = "Not a Guppy method"
    span_label: ClassVar[str] = (
        "Method `{method_name}` of enum `{enum_name}` is not a Guppy function"
    )
    enum_name: str
    method_name: str

    @dataclass(frozen=True)
    class Suggestion(Help):
        message: ClassVar[str] = (
            "Add a `@guppy` annotation to turn `{method_name}` into a Guppy method"
        )

    def __post_init__(self) -> None:
        self.add_sub_diagnostic(NonGuppyMethodError.Suggestion(None))


@dataclass(frozen=True)
class RawEnumDef(TypeDef, ParsableDef):
    """A raw enum type definition that has not been parsed yet.

    This is the initial representation created by the @guppy.enum decorator
    before any parsing or validation has occurred.
    """

    python_class: type
    params: None = field(default=None, init=False)  # Params not known yet

    def parse(self, globals: Globals, sources: SourceMap) -> "ParsedEnumDef":
        """Parses the raw class object into an AST and checks that it is well-formed.

        This method:
        1. Extracts the Python class source code
        2. Parses it into an AST
        3. Validates the structure
        4. Extracts variants from class body
        5. Returns a ParsedEnumDef ready for type checking

        Args:
            globals: The global definitions available in this scope
            sources: Source map for tracking file locations

        Returns:
            A ParsedEnumDef with validated structure

        Raises:
            GuppyError: If the enum definition is malformed
        """
        frame = DEF_STORE.frames[self.id]
        cls_def = parse_py_class(self.python_class, frame, sources)

        if cls_def.keywords:
            raise GuppyError(UnexpectedError(cls_def.keywords[0], "keyword"))

        # Extract generic parameters (e.g., class MyEnum[T, E]:)
        params = extract_generic_params(cls_def, self.name, globals, "Enum")

        variants: list[UncheckedEnumVariant] = []
        used_variant_names: set[str] = set()
        used_func_names: dict[str, ast.FunctionDef] = {}

        for i, node in enumerate(cls_def.body):
            match i, node:
                # Allow `pass` statements for empty enums
                case _, ast.Pass():
                    pass

                # Allow docstrings at the start
                case 0, ast.Expr(value=ast.Constant(value=v)) if isinstance(v, str):
                    pass

                # Ensure all function definitions are Guppy functions
                case _, ast.FunctionDef(name=name) as node:
                    v = getattr(self.python_class, name)
                    if not isinstance(v, GuppyDefinition):
                        raise GuppyError(NonGuppyMethodError(node, self.name, name))
                    used_func_names[name] = node
                    if name in used_variant_names:
                        raise GuppyError(DuplicateVariantError(node, name))

                # Enum variants: name: Type or name: dict[str, Type]
                case _, ast.AnnAssign(target=ast.Name(id=variant_name)) as node:
                    if node.value:
                        raise GuppyError(UnsupportedError(node.value, "Default variant values"))

                    if variant_name in used_variant_names:
                        raise GuppyError(DuplicateVariantError(node.target, variant_name))
                    # Parse the annotation to extract payload types
                    # Single type: Variant: int  -> [int]
                    # Tuple: Variant: tuple[int, str] -> [int, str]
                    payload_type_asts: list[ast.expr] = []
                    match node.annotation:
                        case ast.Tuple(elts=elts):
                            payload_type_asts = elts
                        case _:
                            payload_type_asts = [node.annotation]

                    variants.append(
                        UncheckedEnumVariant(variant_name, payload_type_asts)
                    )
                    used_variant_names.add(variant_name)

                case _, node:
                    raise GuppyError(UnexpectedError(node, "statement", unexpected_in="enum definition"))

        # Ensure functions don't override enum variants
        if overridden := used_variant_names.intersection(used_func_names.keys()):
            x = overridden.pop()
            raise GuppyError(DuplicateVariantError(used_func_names[x], x))

        return ParsedEnumDef(self.id, self.name, cls_def, params, variants)

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        raise InternalGuppyError("Tried to instantiate raw enum definition")


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
class CheckedEnumDef(TypeDef, CompiledDef):
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

    def generated_methods(self) -> list[CustomFunctionDef]:
        # Generating methods to instantiate enum variants
        return []


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
        This is a TEMPORARY hacky implementation.
    """
    # TODO: The implementation below hijacks the type parsing logic to detect recursive
    #  enums. This is not great since it repeats the work done during checking. We can
    #  get rid of this after resolving the todo in `ParsedEnumDef.check_instantiate()`

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
