"""Rewrite extension declarations as ordinary Guppy declarations."""

from __future__ import annotations

import ast
import json
from pathlib import Path


def _decorator_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _find_decorator(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef, name: str
) -> ast.expr | None:
    return next(
        (
            decorator
            for decorator in node.decorator_list
            if _decorator_name(decorator) == name
        ),
        None,
    )


def _offset(source: bytes, lineno: int, column: int) -> int:
    return (
        sum(len(line) for line in source.splitlines(keepends=True)[: lineno - 1])
        + column
    )


def _end_offset(source: bytes, node: ast.expr | ast.stmt) -> int:
    assert node.end_lineno is not None
    assert node.end_col_offset is not None
    return _offset(source, node.end_lineno, node.end_col_offset)


def _type_decorator(node: ast.ClassDef, decorator: ast.expr, type_name: str) -> str:
    keyword_values: dict[str, str] = {}
    if isinstance(decorator, ast.Call):
        positional_names = ["copyable", "droppable", "name", "params"]
        if len(decorator.args) > len(positional_names):
            raise ValueError("@ext_type accepts at most four positional arguments")
        for name, value in zip(positional_names, decorator.args, strict=False):
            if name != "name":
                keyword_values[name] = ast.unparse(value)
        for keyword in decorator.keywords:
            if keyword.arg is None:
                raise ValueError("@ext_type does not support **kwargs")
            if keyword.arg != "name":
                keyword_values[keyword.arg] = ast.unparse(keyword.value)
    indent = " " * (node.col_offset + 4)
    decorator_lines = [
        "auto_hugr_type(",
        f"{indent}_AUTO_HUGR_EXTENSION,",
        f"{indent}{json.dumps(type_name)},",
    ]
    decorator_lines.extend(
        f"{indent}{name}={value}," for name, value in keyword_values.items()
    )
    decorator_lines.append(f"{' ' * node.col_offset})")
    return "\n".join(decorator_lines)


def _op_decorator(
    node: ast.FunctionDef | ast.AsyncFunctionDef, decorator: ast.expr
) -> str:
    op_name = node.name
    if isinstance(decorator, ast.Call):
        for keyword in decorator.keywords:
            if (
                keyword.arg == "override_name"
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            ):
                op_name = keyword.value.value
    indent = " " * (node.col_offset + 4)
    return "\n".join(
        [
            "hugr_op(",
            f"{indent}auto_hugr_op(_AUTO_HUGR_EXTENSION, {json.dumps(op_name)}),",
            f"{indent}name={json.dumps(op_name)},",
            f"{' ' * node.col_offset})",
        ]
    )


def _extension_prelude(json_name: str) -> str:
    return f"""# isort: split
from pathlib import Path as _Path

from auto_hugr_ext import (
    auto_hugr_op,
    auto_hugr_type,
    load_extension,
)
from guppylang_internals.decorator import hugr_op

_AUTO_HUGR_EXTENSION = load_extension(
    _Path(__file__).with_name({json.dumps(json_name)})
)
"""


def generate_python_module(
    source_path: str | Path,
    extension_json_path: str | Path,
    output_path: str | Path,
) -> Path:
    """Copy a declaration file while replacing `ext_*` decorators with Guppy ones."""
    source_path = Path(source_path)
    extension_json_path = Path(extension_json_path)
    output_path = Path(output_path)
    original = source_path.read_bytes()
    syntax = ast.parse(original, filename=str(source_path))
    edits: list[tuple[int, int, bytes]] = []

    for node in syntax.body:
        if isinstance(node, ast.ClassDef):
            decorator = _find_decorator(node, "ext_type")
            if decorator is not None:
                type_name = node.name
                if isinstance(decorator, ast.Call):
                    for keyword in decorator.keywords:
                        if (
                            keyword.arg == "name"
                            and isinstance(keyword.value, ast.Constant)
                            and isinstance(keyword.value.value, str)
                        ):
                            type_name = keyword.value.value
                edits.append(
                    (
                        _offset(original, decorator.lineno, decorator.col_offset),
                        _end_offset(original, decorator),
                        _type_decorator(node, decorator, type_name).encode(),
                    )
                )
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    op_decorator = _find_decorator(member, "ext_op")
                    if op_decorator is not None:
                        edits.append(
                            (
                                _offset(
                                    original,
                                    op_decorator.lineno,
                                    op_decorator.col_offset,
                                ),
                                _end_offset(original, op_decorator),
                                _op_decorator(member, op_decorator).encode(),
                            )
                        )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decorator = _find_decorator(node, "ext_op")
            if decorator is not None:
                edits.append(
                    (
                        _offset(original, decorator.lineno, decorator.col_offset),
                        _end_offset(original, decorator),
                        _op_decorator(node, decorator).encode(),
                    )
                )
        elif isinstance(node, ast.ImportFrom) and node.module == "auto_hugr_ext":
            remaining = [
                alias
                for alias in node.names
                if alias.name not in {"ext_op", "ext_type"}
            ]
            if len(remaining) != len(node.names):
                replacement = ""
                if remaining:
                    replacement = ast.unparse(
                        ast.ImportFrom(node.module, remaining, node.level)
                    )
                start = _offset(original, node.lineno, 0)
                end = _end_offset(original, node)
                if not replacement:
                    if original[end : end + 2] == b"\r\n":
                        end += 2
                    elif original[end : end + 1] == b"\n":
                        end += 1
                edits.append((start, end, replacement.encode()))

    lines = original.splitlines(keepends=True)
    insert_after = 0
    saw_module_docstring = False
    for node in syntax.body:
        is_docstring = (
            node is syntax.body[0]
            and isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        )
        if is_docstring:
            insert_after = node.end_lineno
            saw_module_docstring = True
            continue
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            insert_after = node.end_lineno
            continue
        if isinstance(node, ast.Import | ast.ImportFrom):
            insert_after = node.end_lineno
            continue
        if node is syntax.body[0] and not saw_module_docstring and insert_after == 0:
            break
        if insert_after:
            break
    insertion_offset = sum(len(line) for line in lines[:insert_after])
    prelude = _extension_prelude(extension_json_path.name).encode()
    separator = b"" if insertion_offset == 0 else b"\n"
    edits.append((insertion_offset, insertion_offset, separator + prelude))

    rewritten = original
    for start, end, replacement in sorted(edits, reverse=True):
        rewritten = rewritten[:start] + replacement + rewritten[end:]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(rewritten)
    return output_path
