"""Regression tests for memory-related issues."""

import gc
import weakref

from guppylang import guppy
from guppylang.std.quantum import h, qubit


def test_definitions_during_tracing_release_previous_modules(validate):
    """Tracing must not keep references to the generated hugrs alive.

    Regression test for <https://github.com/Quantinuum/guppylang/issues/2411>
    """

    def make_gate():
        @guppy
        def gate(q: qubit) -> None:
            later(q)

        # Name resolution needs to see definitions added after @guppy ran.
        #
        # This requires keeping the full frame info alive during tracing.
        @guppy
        def later(q: qubit) -> None:
            h(q)

        return gate

    @guppy.comptime
    def main(q: qubit) -> None:
        gate_from_helper = make_gate()

        @guppy
        def local_gate(q: qubit) -> None:
            # Make sure recursive calls are properly handled.
            def recurse(n: int, q: qubit) -> None:
                if n <= 0:
                    h(q)
                else:
                    recurse(n - 1, q)

            recurse(2, q)

        gate_from_helper(q)
        local_gate(q)

    previous = []
    for _ in range(3):
        package = main.compile_function()
        validate(package)
        gc.collect()
        assert all(module() is None for module in previous)
        previous.append(weakref.ref(package.modules[0]))
        del package


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
