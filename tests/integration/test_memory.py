"""Regression tests for memory-related issues."""

import gc
import weakref

from guppylang import guppy


def test_definitions_during_tracing_release_previous_modules(validate):
    """Definitions created during tracing must not keep their context alive
    unnecessarily.

    Regression test for <https://github.com/Quantinuum/guppylang/issues/2411>
    This used to cause memory leaks when ran repeatedly.
    """

    @guppy.comptime
    def main() -> int:
        @guppy
        def inner() -> int:
            return 1

        return inner()

    first = weakref.ref(main.compile_function().modules[0])
    validate(main.compile_function())
    gc.collect()
    assert first() is None


def test_definitions_from_helpers_release_previous_modules(validate):
    """Definitions created while calling helpers during tracing must not keep
    their context alive unnecessarily.

    Regression test for <https://github.com/Quantinuum/guppylang/issues/2411>
    This used to cause memory leaks when ran repeatedly.
    """

    def make_function():
        @guppy
        def first() -> int:
            return later()

        # Name resolution needs to see definitions added after @guppy ran.
        @guppy
        def later() -> int:
            return 1

        return first

    @guppy.comptime
    def main() -> int:
        inner = make_function()
        return inner()

    first = weakref.ref(main.compile_function().modules[0])
    validate(main.compile_function())
    gc.collect()
    assert first() is None


def test_recursive_nested_definitions_release_previous_modules(validate):
    """Definitions created during recursive tracing must not keep
    their context alive unnecessarily.

    Regression test for <https://github.com/Quantinuum/guppylang/issues/2411>
    This used to cause memory leaks when ran repeatedly.
    """

    @guppy.comptime
    def main() -> int:
        @guppy
        def inner() -> int:
            def recurse(n: int) -> int:
                if n == 0:
                    return 0
                return recurse(n - 1)

            return recurse(1)

        return inner()

    first = weakref.ref(main.compile_function().modules[0])
    validate(main.compile_function())
    gc.collect()
    assert first() is None


def test_recompilation_observes_enclosing_scope_changes(run_int_fn):
    """Snapshotting generated definitions must preserve live enclosing scopes."""
    value = 1

    @guppy.struct
    class Box:
        contents: int

    @guppy
    def main() -> int:
        def read(n: int) -> int:
            if n == 0:
                return value
            return read(n - 1)

        return Box(read(1)).contents

    run_int_fn(main, 1)
    value = 2
    run_int_fn(main, 2)
