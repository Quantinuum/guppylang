"""Regression tests for memory-related issues."""

import gc
import weakref

import pytest

from guppylang import guppy
from guppylang_internals.engine import DEF_STORE, ENGINE


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


class Payload:
    pass


@pytest.mark.parametrize("compile_program", [False, True])
def test_discarded_functions_release_callers(compile_program):
    def build_program():
        @guppy
        def empty() -> None:
            pass

        if compile_program:
            empty.compile()

    def run_once():
        payload = Payload()
        build_program()
        return weakref.ref(payload)

    references = [run_once() for _ in range(3)]
    gc.collect()
    assert all(reference() is None for reference in references)


@pytest.mark.parametrize("kind", ["function", "comptime", "struct", "enum", "unitary"])
def test_discarded_definitions_release_scopes(kind):
    def build():
        payload = Payload()
        if kind == "function":

            @guppy
            def definition() -> None:
                pass
        elif kind == "comptime":

            @guppy.comptime
            def definition() -> int:
                # The Python closure must be collectable along with the definition.
                return int(payload is not None)
        elif kind == "struct":

            @guppy.struct
            class definition:
                value: int

                @guppy
                def get(self: "definition") -> int:
                    return self.value
        elif kind == "enum":

            @guppy.enum
            class definition:
                Empty = {}
        else:

            @guppy.unitary
            class definition:
                @guppy
                def __call__(value: int) -> int:
                    return value

        return weakref.ref(payload), weakref.ref(definition.wrapped)

    previous = set(DEF_STORE.raw_defs)
    references = [reference for _ in range(3) for reference in build()]
    registered = set(DEF_STORE.raw_defs) - previous
    gc.collect()
    assert all(reference() is None for reference in references)
    assert registered.isdisjoint(DEF_STORE.raw_defs)
    assert registered.isdisjoint(DEF_STORE.type_members)
    assert registered.isdisjoint(DEF_STORE.type_member_parents)
    assert registered.isdisjoint(DEF_STORE.custom_modified_defs)
    assert registered.isdisjoint(DEF_STORE.custom_modified_def_parents)


@pytest.mark.parametrize("fail", [False, True])
def test_tracing_releases_discarded_scopes(fail):
    references = []

    @guppy.comptime
    def main() -> int:
        payload = Payload()
        references.append(weakref.ref(payload))

        @guppy
        def unused() -> None:
            pass

        # Definitions must survive GC until the stage has finished using them.
        del unused
        gc.collect()
        if fail:
            raise ValueError("tracing failed")
        return 0

    for _ in range(3):
        if fail:
            with pytest.raises(ValueError, match="tracing failed"):
                main.compile_function()
        else:
            main.compile_function()
    ENGINE.reset()
    gc.collect()
    assert all(reference() is None for reference in references)


def test_rechecking_types_releases_replaced_methods():
    @guppy.struct
    class Box:
        value: int

    Box.check()
    methods = [
        weakref.ref(DEF_STORE.raw_defs[id])
        for id in DEF_STORE.type_members[Box.id].values()
    ]
    Box.check()
    gc.collect()
    assert methods
    assert all(method() is None for method in methods)


def test_library_owns_its_members(validate):
    from guppylang.library import GuppyLibrary

    def build():
        @guppy
        def main() -> int:
            return 1

        return GuppyLibrary.from_members(main)

    library = build()
    gc.collect()
    validate(library.compile())


def test_overload_owns_its_variants(validate):
    def variants():
        @guppy
        def first(x: int) -> int:
            return x

        @guppy
        def second(x: float) -> float:
            return x

        return first, second

    @guppy.overload(*variants())
    def combined(*args): ...

    gc.collect()

    @guppy
    def main() -> int:
        return combined(1)

    validate(main.compile_function())


def test_copied_types_keep_their_definition_alive():
    from copy import deepcopy

    from hugr import tys as ht

    from guppylang_internals.decorator.custom import custom_type
    from guppylang_internals.tys.ty import OpaqueType

    def build():
        return custom_type(ht.Bool)(type("Temporary", (), {}))

    definition = build()
    copied_type = deepcopy(OpaqueType([], definition.wrapped))
    def_id = definition.id
    del definition
    gc.collect()
    assert def_id in DEF_STORE.raw_defs
    assert copied_type.defn is DEF_STORE.raw_defs[def_id]
    del copied_type
    gc.collect()
    assert def_id not in DEF_STORE.raw_defs
