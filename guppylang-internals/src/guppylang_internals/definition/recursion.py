"""Recursive type definition validation for parsed structs and enums."""

import ast
from collections.abc import Iterator
from typing import TYPE_CHECKING, TypeAlias, TypeGuard

from guppylang_internals.ast_util import AstNode
from guppylang_internals.checker.errors.generic import UnsupportedError
from guppylang_internals.definition.common import DefId, Definition
from guppylang_internals.error import GuppyError, InternalGuppyError
from guppylang_internals.tys.parsing import (
    TypeParsingCtx,
    _parse_delayed_annotation,
    _try_parse_defn,
)

if TYPE_CHECKING:
    from guppylang_internals.definition.enum import ParsedEnumDef
    from guppylang_internals.definition.struct import ParsedStructDef


ParsedRecursiveTypeDef: TypeAlias = "ParsedStructDef | ParsedEnumDef"


def check_not_recursive(defn: ParsedRecursiveTypeDef, ctx: TypeParsingCtx) -> None:
    """Raises a user error if a struct or enum definition depends on itself."""
    _check_not_recursive(defn, ctx, [defn.id], set())


def _check_not_recursive(
    defn: ParsedRecursiveTypeDef,
    ctx: TypeParsingCtx,
    path: list[DefId],
    checked: set[DefId],
) -> None:
    for dependency, loc in _dependencies(defn, ctx):
        if dependency.id in path:
            raise GuppyError(UnsupportedError(loc, "Recursive definitions"))
        if dependency.id not in checked:
            dependency_ctx = _type_parsing_ctx(dependency)
            _check_not_recursive(
                dependency, dependency_ctx, [*path, dependency.id], checked
            )

    checked.add(defn.id)


def _dependencies(
    defn: ParsedRecursiveTypeDef, ctx: TypeParsingCtx
) -> Iterator[tuple[ParsedRecursiveTypeDef, AstNode]]:
    for type_ast in _field_type_asts(defn):
        for node in _annotation_nodes(type_ast):
            dependency = _try_parse_defn(node, ctx.globals)
            if _is_parsed_struct_or_enum(dependency):
                yield dependency, node


def _field_type_asts(defn: ParsedRecursiveTypeDef) -> Iterator[ast.expr]:
    from guppylang_internals.definition.enum import ParsedEnumDef
    from guppylang_internals.definition.struct import ParsedStructDef

    if isinstance(defn, ParsedStructDef):
        for field in defn.fields:
            yield field.type_ast
    elif isinstance(defn, ParsedEnumDef):
        for variant in defn.variants.values():
            for field in variant.fields:
                yield field.type_ast
    else:
        raise InternalGuppyError("Expected a parsed struct or enum definition")


def _type_parsing_ctx(defn: ParsedRecursiveTypeDef) -> TypeParsingCtx:
    """Returns a type parsing context for the definition's own module scope.

    Recursive checks may walk into definitions imported from other modules, so their
    field annotations must be resolved against the frame where they were defined.
    """
    from guppylang_internals.checker.core import Globals
    from guppylang_internals.engine import DEF_STORE

    param_var_mapping = {p.name: p for p in defn.params}
    return TypeParsingCtx(Globals(DEF_STORE.frames[defn.id]), param_var_mapping)


def _annotation_nodes(node: ast.expr) -> Iterator[ast.expr]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        node = _parse_delayed_annotation(node.value, node)

    yield node
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.expr):
            yield from _annotation_nodes(child)


def _is_parsed_struct_or_enum(
    defn: Definition | None,
) -> TypeGuard[ParsedRecursiveTypeDef]:
    from guppylang_internals.definition.enum import ParsedEnumDef
    from guppylang_internals.definition.struct import ParsedStructDef

    return isinstance(defn, ParsedStructDef | ParsedEnumDef)
