import functools
import inspect
from types import FunctionType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

import pytest
from guppylang import guppy
from guppylang_internals.ast_util import get_file
from guppylang_internals.checker.errors.generic import ExpectedError
from guppylang_internals.definition.function import parse_py_func
from guppylang_internals.diagnostic import DiagnosticsRenderer
from guppylang_internals.span import SourceMap, to_span


@pytest.mark.parametrize("wrapper_count", [0, 1, 2])
@pytest.mark.parametrize("copy_module", [False, True])
def test_wrapped_function_source(wrapper_count: int, copy_module: bool) -> None:
    def original() -> int:
        """The original docstring."""
        return 42

    wrapped: Callable[..., object] = original
    for index in range(wrapper_count):

        def placeholder(*args: object, **kwargs: object) -> None:
            pass

        wrapper = FunctionType(
            placeholder.__code__.replace(co_filename=f"<generated-wrapper-{index}>"),
            {"__name__": "generated_decorators"},
        )
        assigned = functools.WRAPPER_ASSIGNMENTS
        if not copy_module:
            assigned = tuple(name for name in assigned if name != "__module__")
        wrapped = functools.wraps(wrapped, assigned=assigned)(wrapper)

    sources = SourceMap()
    node, docstring = parse_py_func(wrapped, sources)
    expected_file = inspect.getsourcefile(original)
    assert get_file(node) == expected_file
    assert set(sources.sources) == {expected_file}
    assert docstring == original.__doc__
    assert sources.span_lines(to_span(node)) == [
        "    def original() -> int:",
        '        """The original docstring."""',
        "        return 42",
    ]

    diagnostic = ExpectedError(node.body[0], "an integer")
    renderer = DiagnosticsRenderer(sources)
    renderer.render_diagnostic(diagnostic)
    assert "return 42" in "\n".join(renderer.buffer)
    assert "<generated-wrapper-" not in "\n".join(renderer.buffer)

    guppy(wrapped).check()
