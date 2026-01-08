import ast
import keyword
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.core import Globals
from guppylang_internals.checker.errors.generic import (
    UnexpectedError,
)
from guppylang_internals.definition.common import (
    CheckableDef,
    CompiledDef,
    ParsableDef,
)
from guppylang_internals.definition.custom import (
    CustomFunctionDef,
)
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.definition.util import (
    DuplicateFieldError,
    extract_generic_params,
    parse_py_class,
)
from guppylang_internals.diagnostic import Help
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.error import GuppyError, InternalGuppyError
from guppylang_internals.span import SourceMap
from guppylang_internals.tys.arg import Argument
from guppylang_internals.tys.param import Parameter
from guppylang_internals.tys.parsing import TypeParsingCtx, type_from_ast
from guppylang_internals.tys.ty import (
    Type,
)

if sys.version_info >= (3, 12):
    pass


@dataclass(frozen=True)
class EnumHelp(Help):
    message: ClassVar[str] = (
        'Enum variants must be of the form `VariantName = {{"var1": Type1, ...}}`'
    )


# TODO: Considering renaming to UncheckedField and CheckedField,
# and joining with UncheckedStructField and StructField
@dataclass(frozen=True)
class UncheckedEnumVariantField:
    """A single field on a enum variant whose type has not been checked yet."""

    name: str
    type_ast: ast.expr


@dataclass(frozen=True)
class EnumVariantField:
    """A single field on a enum variant."""

    name: str
    ty: Type


@dataclass(frozen=True)
class UncheckedEnumVariant:
    """A single field on a enum whose type has not been checked yet."""

    # TODO: value in AST form?
    name: str
    variant_fields: Sequence[UncheckedEnumVariantField]


@dataclass(frozen=True)
class EnumVariant:
    """A single field on a struct."""

    name: str
    fields: Sequence[EnumVariantField]


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
        variants: dict[str, UncheckedEnumVariant] = {}
        used_variant_names: set[str] = set()
        for i, node in enumerate(cls_def.body):
            match i, node:
                # TODO: do we allow `pass` statements to define empty enum?
                case _, ast.Pass():
                    pass
                # Docstrings are also fine if they occur at the start
                case 0, ast.Expr(value=ast.Constant(value=v)) if isinstance(v, str):
                    pass
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
                    if variant_name in used_variant_names:
                        raise GuppyError(
                            DuplicateFieldError(
                                node.targets[0],
                                self.name,
                                variant_name,
                                class_type="Enum",
                            )
                        )
                    # TODO: is that what we need? (a list of EnumVariant)
                    assert isinstance(node.value, ast.Dict)  # for mypy
                    variants[variant_name] = parse_enum_variant(
                        variant_name, node.value
                    )
                    used_variant_names.add(variant_name)
                # if unexpected statement are found
                case _, node:
                    err = UnexpectedError(
                        node,
                        "statement",
                        unexpected_in="enum variant definition",
                    )
                    err.add_sub_diagnostic(EnumHelp(None))
                    raise GuppyError(err)
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
    variants: Mapping[str, UncheckedEnumVariant]

    def check(self, globals: Globals) -> "CheckedEnumDef":
        """Checks that all enum fields have valid types."""
        param_var_mapping = {p.name: p for p in self.params}
        ctx = TypeParsingCtx(globals, param_var_mapping)

        # TODO: not ideal, see `ParsedStructDef.check_instantiate`
        # TODO: temporarily commented, see best way to do it
        # check_not_recursive(self, ctx)

        variants: dict[str, EnumVariant] = {}
        # loop over variants to check their fields
        for name, variant in self.variants.items():
            fields: list[EnumVariantField] = [
                EnumVariantField(field.name, type_from_ast(field.type_ast, ctx))
                for field in variant.variant_fields
            ]
            variants[name] = EnumVariant(name, fields)

        return CheckedEnumDef(
            self.id, self.name, self.defined_at, self.params, variants
        )

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        """Checks if the enum can be instantiated with the given arguments."""
        # TODO: here
        raise NotImplementedError


@dataclass(frozen=True)
class CheckedEnumDef(TypeDef, CompiledDef):
    """Docstring for CheckedEnumDef"""

    defined_at: ast.ClassDef
    params: Sequence[Parameter]
    variants: Mapping[str, EnumVariant]

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        """Checks if the enum can be instantiated with the given arguments."""
        # TODO
        raise NotImplementedError

    def generated_methods(self) -> list[CustomFunctionDef]:
        # Generating methods to instantiate enum variants
        return []


def parse_enum_variant(name: str, dict_ast: ast.Dict) -> UncheckedEnumVariant:
    variant_fields: list[UncheckedEnumVariantField] = []
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
                            k, name, key_name, class_type="Enum Variant"
                        )
                    )
                variant_field_names.append(key_name)
                variant_fields.append(UncheckedEnumVariantField(key_name, v))
            case _:
                err = UnexpectedError(
                    dict_ast,
                    "expression",
                    unexpected_in="enum variant definition",
                )
                err.add_sub_diagnostic(EnumHelp(None))
                raise GuppyError(err)

    return UncheckedEnumVariant(name, variant_fields)
