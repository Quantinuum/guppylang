"""Loads a source file and resolves the guppy types of everything it declares."""

from __future__ import annotations

import ast
import importlib.util
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from guppylang_internals.definition.common import DefId
from guppylang_internals.definition.custom import CustomFunctionDef
from guppylang_internals.definition.ty import OpaqueTypeDef
from guppylang_internals.engine import DEF_STORE, ENGINE

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType

    from guppylang_internals.tys.ty import FunctionType


@dataclass(frozen=True)
class ExtTypeEntry:
    name: str
    defn: OpaqueTypeDef
    copyable: bool
    droppable: bool


@dataclass(frozen=True)
class ResolvedOp:
    name: str
    qualified_name: str
    ty: FunctionType


@dataclass(frozen=True)
class HarvestedExtension:
    types: list[ExtTypeEntry]
    ops: list[ResolvedOp]


def _decorator_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _has_decorator(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef, name: str
) -> bool:
    return any(_decorator_name(decorator) == name for decorator in node.decorator_list)


def _definition_id(value: object) -> DefId:
    defn = getattr(value, "wrapped", None)
    identifier = getattr(defn, "id", None)
    if not isinstance(identifier, DefId):
        raise TypeError(f"Expected a decorated Guppy definition, got {value!r}")
    return identifier


def load_module(source_path: Path) -> ModuleType:
    """Executes the given source file so that its decorators register themselves."""
    source_path = source_path.resolve()
    module_name = f"_auto_hugr_ext_target_{source_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, source_path)
    if spec is None or spec.loader is None:
        msg = f"Cannot load a Python module from {source_path}"
        raise ValueError(msg)
    module = importlib.util.module_from_spec(spec)
    parent = str(source_path.parent)
    added = parent not in sys.path
    if added:
        sys.path.insert(0, parent)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)
        if added:
            sys.path.remove(parent)
    return module


def harvest(source_path: Path) -> HarvestedExtension:
    """Loads `source_path` and resolves the signature of every declared op."""
    source_path = source_path.resolve()
    module = load_module(source_path)
    syntax = ast.parse(source_path.read_text(encoding="utf-8"))
    types: list[ExtTypeEntry] = []
    ops = []
    for node in syntax.body:
        if isinstance(node, ast.ClassDef) and _has_decorator(node, "ext_type"):
            wrapped_type = module.__dict__[node.name].wrapped
            if not isinstance(wrapped_type, OpaqueTypeDef):
                raise TypeError(f"@ext_type {node.name} did not create an opaque type")
            types.append(
                ExtTypeEntry(
                    wrapped_type.name,
                    wrapped_type,
                    not wrapped_type.never_copyable,
                    not wrapped_type.never_droppable,
                )
            )
            for member in node.body:
                if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if _has_decorator(member, "ext_op"):
                    member_id = DEF_STORE.type_members[wrapped_type.id][member.name]
                    ops.append(
                        _resolve_op(
                            wrapped_type.name,
                            member_id,
                        )
                    )
        elif isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef)
        ) and _has_decorator(node, "ext_op"):
            ops.append(_resolve_op(None, _definition_id(module.__dict__[node.name])))
    return HarvestedExtension(types, ops)


def _resolve_op(owner: str | None, def_id: DefId) -> ResolvedOp:
    parsed = ENGINE.get_parsed(def_id)
    if not isinstance(parsed, CustomFunctionDef):
        raise TypeError(f"@ext_op {def_id} did not create a custom function")
    qualified_name = f"{owner}.{parsed.name}" if owner else parsed.name
    return ResolvedOp(parsed.name, qualified_name, parsed.ty)
