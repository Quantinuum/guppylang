"""Regression tests for memory-related issues."""

import gc
import weakref

import pytest

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


@pytest.mark.parametrize("fail", [False, True])
@pytest.mark.parametrize("nested", [False, True])
def test_custom_call_checker_releases_context(fail, nested):
    from contextlib import nullcontext

    from guppylang_internals.definition.custom import CustomCallChecker

    class Payload:
        pass

    class Checker(CustomCallChecker):
        def synthesize(self, args):
            raise NotImplementedError

    checker = Checker()

    def check():
        context, node, function = Payload(), Payload(), Payload()
        references = [weakref.ref(value) for value in (context, node, function)]
        with (
            pytest.raises(ValueError, match="checking failed")
            if fail
            else nullcontext()
        ):
            with checker._setup(context, node, function):
                if nested:
                    with checker._setup(context, node, function):
                        pass
                    assert checker.ctx is context
                if fail:
                    raise ValueError("checking failed")
        return references

    references = check()
    gc.collect()
    assert all(reference() is None for reference in references)
    assert not hasattr(checker, "ctx")
    assert not hasattr(checker, "node")
    assert not hasattr(checker, "func")
