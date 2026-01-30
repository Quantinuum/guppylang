import ast
import keyword
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import ClassVar, Generic, TypeVar

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
from guppylang_internals.tys.param import Parameter
from guppylang_internals.tys.parsing import TypeParsingCtx, type_from_ast
from guppylang_internals.tys.ty import (
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
        # TODO: temporarily commented, see best way to do it
        # check_not_recursive(self, ctx)

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
        # TODO: here
        raise NotImplementedError


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
        # TODO
        raise NotImplementedError

    def generated_methods(self) -> list[CustomFunctionDef]:
        # Generating methods to instantiate enum variants
        return []


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
