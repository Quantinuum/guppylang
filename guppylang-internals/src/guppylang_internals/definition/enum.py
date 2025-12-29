import ast
import inspect
import linecache
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from types import FrameType
from typing import ClassVar
from unittest import case

from hugr import Wire, ops

from guppylang_internals.ast_util import AstNode, annotate_location
from guppylang_internals.checker.core import Globals
from guppylang_internals.checker.errors.generic import (
    ExpectedError,
    UnexpectedError,
    UnsupportedError,
)
from guppylang_internals.compiler.core import GlobalConstId
from guppylang_internals.definition.common import (
    CheckableDef,
    CompiledDef,
    DefId,
    ParsableDef,
    UnknownSourceError,
)
from guppylang_internals.definition.custom import (
    CustomCallCompiler,
    CustomFunctionDef,
    DefaultCallChecker,
)
from guppylang_internals.definition.function import parse_source
from guppylang_internals.definition.parameter import ParamDef
from guppylang_internals.definition.ty import TypeDef
from guppylang_internals.diagnostic import Error, Help, Note
from guppylang_internals.engine import DEF_STORE
from guppylang_internals.error import GuppyError, InternalGuppyError
from guppylang_internals.ipython_inspect import is_running_ipython
from guppylang_internals.span import SourceMap, Span, to_span
from guppylang_internals.tys.arg import Argument
from guppylang_internals.tys.param import Parameter, check_all_args
from guppylang_internals.tys.parsing import TypeParsingCtx, type_from_ast
from guppylang_internals.tys.ty import (
    FuncInput,
    FunctionType,
    InputFlags,
    StructType,
    Type,
)
from guppylang_internals.definition.struct import (
    DuplicateFieldError,
    RedundantParamsError,
    check_not_recursive,
    params_from_ast,
    parse_py_class,
    try_parse_generic_base,
)


if sys.version_info >= (3, 12):
    from guppylang_internals.tys.parsing import parse_parameter


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


# TODO: Considering renaming to UncheckedField and CheckedField,
# and joining with UncheckedStructField and StructField
@dataclass(frozen=True)
class UncheckedEnumVariant:
    """A single field on a enum whose type has not been checked yet."""

    # TODO: value in AST form?
    name: str
    variant_fields: list[UncheckedEnumVariantField]


@dataclass(frozen=True)
class EnumVariant:
    """A single field on a struct."""

    name: str
    fields: list[EnumVariantField]


@dataclass(frozen=True)
class RawEnumDef(TypeDef, ParsableDef):
    """A raw enum type definition before parsing."""

    python_class: type
    params: None = field(default=None, init=False)  # Params not known yet

    def parse(self, globals: "Globals", sources: SourceMap) -> "ParsedEnumDef":
        """Parses the raw class object into an AST and checks that it is well-formed."""
        print("DEBUG: I'm parsing enum")
        frame = DEF_STORE.frames[self.id]
        """
        cls_node = ast.parse("class _:\n" + source).body[0]
        assert isinstance(cls_node, ast.ClassDef)
        cls_def = cls_node.body[0]
        """
        cls_def = parse_py_class(self.python_class, frame, sources)
        print(cls_def)

        if cls_def.keywords:
            raise GuppyError(UnexpectedError(cls_def.keywords[0], "keyword"))

        # Look for generic parameters from Python 3.12 style syntax
        params = []
        params_span: Span | None = None
        if sys.version_info >= (3, 12):
            if cls_def.type_params:
                first, last = cls_def.type_params[0], cls_def.type_params[-1]
                params_span = Span(to_span(first).start, to_span(last).end)
                param_vars_mapping: dict[str, Parameter] = {}
                for idx, param_node in enumerate(cls_def.type_params):
                    param = parse_parameter(
                        param_node, idx, globals, param_vars_mapping
                    )
                    param_vars_mapping[param.name] = param
                    params.append(param)

        # The only base we allow is `Generic[...]` to specify generic parameters with
        # the legacy syntax
        # Assuming is the same as struct
        match cls_def.bases:
            case []:
                pass
            case [base] if elems := try_parse_generic_base(base):
                # Complain if we already have Python 3.12 generic params
                if params_span is not None:
                    err: Error = RedundantParamsError(base, self.name)
                    err.add_sub_diagnostic(RedundantParamsError.PrevSpec(params_span))
                    raise GuppyError(err)
                params = params_from_ast(elems, globals)
            case bases:
                err = UnsupportedError(bases[0], "Enum inheritance", singular=True)
                raise GuppyError(err)

        # we look for variants in the class body
        variants: list[UncheckedEnumVariant] = []
        used_variant_names: set[str] = set()
        for i, node in enumerate(cls_def.body):
            match i, node:
                # TODO: do we allow `pass` statements to define empty enum?
                case _, ast.Pass():
                    pass
                # Docstrings are also fine if they occur at the start
                case 0, ast.Expr(value=ast.Constant(value=v)) if isinstance(v, str):
                    pass
                # Enum variant are declared via dictionary, where key are the variant fields and values are types;
                # e.g. `variant = {"a": int, ...}
                # multi assignment: a = b = 1 are not supported
                # TODO: support inline assignment e.g. v1, v2 = {}, {}
                # TODO: do we allow variant=function(...)? this is more a metaprogramming feature
                case (
                    _,
                    ast.Assign(
                        targets=[ast.Name(id=variant_name)], value=ast.Dict()
                    ) as node,
                ):
                    if variant_name in used_variant_names:
                        err = DuplicateFieldError(
                            node.targets[0], self.name, variant_name, class_type="Enum"
                        )
                        raise GuppyError(err)
                    # TODO: what we need? I parse the dictionary and get field types
                    variants.append(parse_enum_variant(variant_name, node.value))
                    used_variant_names.add(variant_name)
                # if unexpected statement are found
                case _, node:
                    print(ast)
                    err = UnexpectedError(
                        node, "statement", unexpected_in="enum variant definition"
                    )
                    err.add_sub_diagnostic(
                        UnexpectedError.Fix(
                            None,
                            'Enum variant must be of form `VariantName = {{"var1": Type1, ...}}`',
                        )
                    )
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
    variants: Sequence[UncheckedEnumVariant]

    def check(self, globals: Globals) -> "CheckedEnumDef":
        """Checks that all enum fields have valid types."""
        print("DEBUG: I'm checking enum", self.name)
        param_var_mapping = {p.name: p for p in self.params}
        ctx = TypeParsingCtx(globals, param_var_mapping)

        # TODO: not ideal, see `ParsedStructDef.check_instantiate`
        # TODO: temporarily commented, see best way to do it
        # check_not_recursive(self, ctx)

        variants: list[EnumVariant] = []
        for variant in self.variants:
            fields: list[EnumVariantField] = [
                EnumVariantField(field.name, type_from_ast(field.type_ast, ctx))
                for field in variant.variant_fields
            ]
            variants.append(EnumVariant(variant.name, fields))

        print("DEBUG: variants:")
        for v in variants:
            print(v)

        return CheckedEnumDef(
            self.id, self.name, self.defined_at, self.params, variants
        )

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        """Checks if the enum can be instantiated with the given arguments."""
        print("DEBUG: checking enum instantiation (inside ParsedEnumDef)", self.name)
        # TODO: heree

        return super().check_instantiate(args, loc)

    pass


@dataclass(frozen=True)
class CheckedEnumDef(TypeDef, CompiledDef):
    """Docstring for CheckedEnumDef"""

    defined_at: ast.ClassDef
    params: Sequence[Parameter]
    variants: Sequence[EnumVariant]

    def check_instantiate(
        self, args: Sequence[Argument], loc: AstNode | None = None
    ) -> Type:
        # TODO
        return super().check_instantiate(args, loc)

    """Chechks instantiation of this enum type."""

    def generated_methods(self) -> list[CustomFunctionDef]:
        # Generating methods to instantiate enum variants
        return []

    pass


def parse_enum_variant(name: str, dict_ast: ast.Dict) -> UncheckedEnumVariant:
    # TODO: now this allow variant like `v1 = {"1": int}`
    # we need to prevent this
    variant_fields: list[UncheckedEnumVariantField] = []
    variant_field_names = []
    # we parse the enum variant to get the enum variant fields
    for k, v in zip(dict_ast.keys, dict_ast.values):
        match k:
            case ast.Constant(value=key_name) if isinstance(key_name, str):
                if key_name in variant_field_names:
                    err = DuplicateFieldError(
                        k, name, key_name, class_type="Enum Variant"
                    )
                    raise GuppyError(err)
                variant_field_names.append(key_name)
                variant_fields.append(UncheckedEnumVariantField(key_name, v))
            case _:
                err = UnexpectedError(
                    dict_ast,
                    "expression",
                    unexpected_in="enum variant definition",
                )
                err.add_sub_diagnostic(
                    UnexpectedError.Fix(
                        None,
                        'Enum variant must be of form `VariantName = {{"var1": Type1, ...}}`',
                    )
                )
                raise GuppyError(err)
        # adding field
    return UncheckedEnumVariant(name, variant_fields)
