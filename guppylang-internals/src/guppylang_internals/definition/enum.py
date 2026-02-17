import ast
import keyword
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import ClassVar, Generic, TypeVar

from hugr import Wire, ops

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.core import Globals
from guppylang_internals.checker.errors.generic import (
    UnexpectedError,
    UnsupportedError,
)
from guppylang_internals.compiler.core import GlobalConstId
from guppylang_internals.definition.common import (
    CheckableDef,
    CompiledDef,
    DefId,
    ParsableDef,
)
from guppylang_internals.definition.custom import (
    CustomCallCompiler,
    CustomFunctionDef,
    DefaultCallChecker,
)
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.definition.util import (
    CheckedField,
    DuplicateFieldError,
    NonGuppyMethodError,
    UncheckedField,
    extract_generic_params,
    parse_py_class,
)
from guppylang_internals.diagnostic import Error, Help
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.error import GuppyError, InternalGuppyError
from guppylang_internals.span import SourceMap
from guppylang_internals.tys.arg import Argument
from guppylang_internals.tys.param import Parameter, check_all_args
from guppylang_internals.tys.parsing import TypeParsingCtx, type_from_ast
from guppylang_internals.tys.ty import (
    EnumType,
    FuncInput,
    FunctionType,
    InputFlags,
    Type,
)


@dataclass(frozen=True)
class DuplicateVariantError(Error):
    title: ClassVar[str] = "Duplicate variant"
    span_label: ClassVar[str] = (
        "Enum `{class_name}` already contains a variant named `{variant_name}`"
    )
    class_name: str
    variant_name: str


@dataclass(frozen=True)
class VariantFormHint(Help):
    message: ClassVar[str] = (
        'Enum can contain only variants of the form `VariantName = {{"var1": Type1, ...}}`'  # noqa: E501
        "or `@guppy` annotated methods"
    )


F = TypeVar("F", UncheckedField, CheckedField)


@dataclass(frozen=True)
class EnumVariant(Generic[F]):
    index: int
    name: str
    fields: Sequence[F]


@dataclass(frozen=True)
class RawEnumDef(TypeDef, ParsableDef):
    """A raw enum type definition before parsing."""

    python_class: type
    params: None = field(default=None, init=False)  # Params not known yet

    def parse(self, globals: "Globals", sources: SourceMap) -> "ParsedEnumDef":
        """Parses the raw class object into an AST and checks that it is well-formed."""
        frame = DEF_STORE.frames[self.id]
        cls_def = parse_py_class(self.python_class, frame, sources)
        if cls_def.keywords:
            raise GuppyError(UnexpectedError(cls_def.keywords[0], "keyword"))

        # Look for generic parameters from Python 3.12 style syntax
        params = extract_generic_params(cls_def, self.name, globals, "Enum")

        # We look for variants in the class body
        variants: dict[str, EnumVariant[UncheckedField]] = {}
        used_func_names: dict[str, ast.FunctionDef] = {}
        variant_index = 0
        for i, node in enumerate(cls_def.body):
            match i, node:
                # TODO: do we allow `pass` statements to define empty enum?
                case _, ast.Pass():
                    pass
                # Docstrings are also fine if they occur at the start
                case 0, ast.Expr(value=ast.Constant(value=v)) if isinstance(v, str):
                    pass
                case _, ast.FunctionDef(name=name) as node:
                    used_func_names[name] = node
                # Enum variant are declared via dictionary, where key are the variant
                # fields and values are types;
                # e.g. `variant = {"a": int, ...}
                # We do not support:
                #  - multi assignment: a = b = 1 are not supported
                #  - inline assignment e.g. v1, v2 = {}, {}
                # - variant=function(...)? [this is more a metaprogramming feature]
                case (
                    _,
                    ast.Assign(
                        targets=[ast.Name(id=variant_name)], value=ast.Dict()
                    ) as node,
                ):
                    if variant_name in variants:
                        raise GuppyError(
                            DuplicateVariantError(
                                node.targets[0], self.name, variant_name
                            )
                        )
                    assert isinstance(node.value, ast.Dict)  # for mypy
                    variants[variant_name] = parse_enum_variant(
                        variant_index, variant_name, node.value
                    )
                    variant_index += 1
                # if unexpected statement are found
                case _, node:
                    err = UnexpectedError(
                        node,
                        "statement",
                        unexpected_in="enum definition",
                    )
                    err.add_sub_diagnostic(VariantFormHint(None))
                    raise GuppyError(err)

        # Ensure that functions do not override enum variants
        # and that all functions are Guppy functions
        for func_name, func_def in used_func_names.items():
            from guppylang.defs import GuppyDefinition

            if func_name in variants:
                raise GuppyError(
                    DuplicateVariantError(
                        used_func_names[func_name], self.name, func_name
                    )
                )
            v = getattr(self.python_class, func_name)
            if not isinstance(v, GuppyDefinition):
                raise GuppyError(
                    NonGuppyMethodError(func_def, self.name, func_name, "enum")
                )

        return ParsedEnumDef(self.id, self.name, cls_def, params, variants)

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        raise InternalGuppyError("Tried to instantiate raw enum definition")


@dataclass(frozen=True)
class ParsedEnumDef(TypeDef, CheckableDef):
    """An enum definition whose fields have not been checked yet."""

    defined_at: ast.ClassDef
    params: Sequence[Parameter]
    variants: Mapping[str, EnumVariant[UncheckedField]]

    def check(self, globals: Globals) -> "CheckedEnumDef":
        """Checks that all enum fields have valid types."""
        param_var_mapping = {p.name: p for p in self.params}
        ctx = TypeParsingCtx(globals, param_var_mapping)

        # TODO: not ideal, see `ParsedStructDef.check_instantiate`
        check_not_recursive(self, ctx)

        checked_variants: dict[str, EnumVariant[CheckedField]] = {}
        # loop over variants to check their fields
        for name, variant in self.variants.items():
            fields: list[CheckedField] = [
                CheckedField(field.name, type_from_ast(field.type_ast, ctx))
                for field in variant.fields
            ]
            checked_variants[name] = EnumVariant(variant.index, name, fields)

        return CheckedEnumDef(
            self.id, self.name, self.defined_at, self.params, checked_variants
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
        #  refactor...
        checked_def = self.check(globals)
        return EnumType(args, checked_def)


@dataclass(frozen=True)
class CheckedEnumDef(TypeDef, CompiledDef):
    """An enum definition that has been fully checked."""

    defined_at: ast.ClassDef
    params: Sequence[Parameter]
    variants: Mapping[str, EnumVariant[CheckedField]]

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        """Checks if the enum can be instantiated with the given arguments."""
        check_all_args(self.params, args, self.name, loc)

        return EnumType(args, self)

    def generated_methods(self) -> list[CustomFunctionDef]:
        # Generating methods to instantiate enum variants
        # return []

        @dataclass
        class ConstructorCompiler(CustomCallCompiler):
            """Compiler for the enum variant constructors."""

            idex_variant: int
            type_enum: EnumType

            def compile(self, wires: list[Wire]) -> list[Wire]:
                return list(
                    self.builder.add(
                        ops.Tag(self.idex_variant, self.type_enum.to_hugr(self.ctx))(
                            *wires
                        )
                    )
                )

        variants_constructors = []
        for variant_name, variant in self.variants.items():
            enum_type = EnumType(
                defn=self, args=[p.to_bound(i) for i, p in enumerate(self.params)]
            )
            constructor_sig = FunctionType(
                inputs=[
                    FuncInput(
                        f.ty,
                        InputFlags.Owned if f.ty.linear else InputFlags.NoFlags,
                        f.name,
                    )
                    for f in variant.fields
                ],
                output=enum_type,
                params=self.params,
            )

            constructor_def = CustomFunctionDef(
                id=DefId.fresh(),
                name=variant_name,
                defined_at=self.defined_at,
                ty=constructor_sig,
                call_checker=DefaultCallChecker(),
                call_compiler=ConstructorCompiler(
                    variant.index, enum_type
                ),
                higher_order_value=True,
                higher_order_func_id=GlobalConstId.fresh(f"{self.name}.{variant_name}"),
                has_signature=True,
            )
            variants_constructors.append(constructor_def)

        return variants_constructors


def parse_enum_variant(
    index: int, name: str, dict_ast: ast.Dict
) -> EnumVariant[UncheckedField]:
    variant_fields: list[UncheckedField] = []
    variant_field_names = []
    # we parse the enum variant to get the enum variant fields
    for k, v in zip(dict_ast.keys, dict_ast.values, strict=True):
        match k:
            case ast.Constant(value=str(key_name)):
                # check validity of field name
                if not key_name.isidentifier() or keyword.iskeyword(key_name):
                    raise GuppyError(
                        UnexpectedError(
                            k,
                            "field name",
                            unexpected_in="enum variant definition",
                        )
                    )
                if key_name in variant_field_names:
                    raise GuppyError(
                        DuplicateFieldError(
                            k, name, key_name, class_type="Enum variant"
                        )
                    )
                variant_field_names.append(key_name)
                variant_fields.append(UncheckedField(key_name, v))
            case _:
                err = UnexpectedError(
                    dict_ast,
                    "expression",
                    unexpected_in="enum variant definition",
                )
                err.add_sub_diagnostic(VariantFormHint(None))
                raise GuppyError(err)

    return EnumVariant(index, name, variant_fields)


def check_not_recursive(defn: ParsedEnumDef, ctx: TypeParsingCtx) -> None:
    """Throws a user error if the given enum definition is recursive.

    This function temporarily replaces the enum's check_instantiate method with
    a dummy that raises an error. Then it attempts to parse all variant field
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
        raise GuppyError(UnsupportedError(loc, "Recursive definitions"))

    # Save the original check_instantiate method
    original = defn.check_instantiate

    # Temporarily replace it with the dummy that raises on recursion
    object.__setattr__(defn, "check_instantiate", dummy_check_instantiate)

    try:
        # Attempt to parse all variant field types
        # Note: defn.variants is a Mapping[str, EnumVariant[UncheckedField]]
        for variant in defn.variants.values():
            for field in variant.fields:
                type_from_ast(field.type_ast, ctx)
    finally:
        # Always restore the original method
        object.__setattr__(defn, "check_instantiate", original)
