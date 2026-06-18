import ast

import pytest
from guppylang_internals.ast_util import annotate_location
from guppylang_internals.span import function_header_span, to_span


def _parse_func(source: str) -> ast.FunctionDef:
    node = ast.parse(source).body[0]
    assert isinstance(node, ast.FunctionDef)
    annotate_location(node, source, "test.py", 1)
    return node


def _header_text(func_def: ast.FunctionDef) -> str:
    span = function_header_span(func_def)
    source = func_def.source  # type: ignore[attr-defined]
    lines = source.splitlines()
    if span.is_multiline:
        parts = [lines[span.start.line - 1][span.start.column :]]
        parts.extend(
            lines[line_no - 1] for line_no in range(span.start.line + 1, span.end.line)
        )
        parts.append(lines[span.end.line - 1][: span.end.column])
        return "\n".join(parts)
    line = lines[span.start.line - 1]
    return line[span.start.column : span.end.column]


@pytest.mark.parametrize(
    ("source", "expected_header"),
    [
        ("def foo():\n    return", "def foo():"),
        ("def foo(x: bool):\n    return x", "def foo(x: bool):"),
        ("def foo(\n    x: bool,\n):\n    return x", "def foo(\n    x: bool,\n):"),
        ("def foo() :\n    return", "def foo() :"),
    ],
)
def test_function_header_span(source: str, expected_header: str) -> None:
    func_def = _parse_func(source)
    assert _header_text(func_def) == expected_header
    assert function_header_span(func_def).end <= to_span(func_def).end
