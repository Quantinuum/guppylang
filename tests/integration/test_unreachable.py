import warnings

import pytest

from guppylang import guppy, qubit
from guppylang import GuppyWarning
from guppylang_internals.error import GuppyError
from guppylang.std.quantum import discard, h
from tests.util import compile_guppy, guppy_warning_records


def assert_unreachable_warning_emitted(fn):
    """Assert that running `fn` emits exactly one unreachable-code warning."""

    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        result = fn()

    guppy_records = guppy_warning_records(records)
    assert len(guppy_records) == 1
    warning = guppy_records[0]
    assert warning.category is GuppyWarning
    assert str(warning.message) == "Unreachable: This code is not reachable"
    return result


def test_var_defined1(validate):
    @compile_guppy
    def test() -> int:
        if True:
            x = 1
        return x

    validate(test)


def test_var_defined2(validate):
    @compile_guppy
    def test(b: bool) -> int:
        while True:
            if b:
                x = 1
                break
        return x

    validate(test)


def test_type_mismatch1(validate):
    def compile_test():
        @compile_guppy
        def test() -> int:
            if True:
                x = 1
            else:
                x = 1.0
            return x

        return test

    validate(assert_unreachable_warning_emitted(compile_test))


def test_type_mismatch2(validate):
    def compile_test():
        @compile_guppy
        def test() -> int:
            x = 1
            while False:
                x = 1.0
            return x

        return test

    validate(assert_unreachable_warning_emitted(compile_test))


def test_type_mismatch3(validate):
    def compile_test():
        @compile_guppy
        def test() -> int:
            x = 1
            if False and (x := 1.0):
                pass
            return x

        return test

    validate(assert_unreachable_warning_emitted(compile_test))


def test_unused_var_use1(validate):
    def compile_test():
        @compile_guppy
        def test() -> int:
            x = 1
            if True:
                return 0
            return x

        return test

    validate(assert_unreachable_warning_emitted(compile_test))


def test_unused_var_use2(validate):
    def compile_test():
        @compile_guppy
        def test() -> int:
            x = 1
            if not False:
                x = 1.0
                return 0
            return x

        return test

    validate(assert_unreachable_warning_emitted(compile_test))


def test_unreachable_leak(validate):
    @guppy
    def test(b: bool) -> int:
        q = qubit()
        while True:
            if b:
                discard(q)
                return 1
        # This return would leak, but we don't complain since it's unreachable:
        return 0

    validate(assert_unreachable_warning_emitted(test.compile_function))


def test_unreachable_leak2(validate):
    @guppy
    def test() -> None:
        if False:
            # This would leak, but we don't complain since it's unreachable:
            q = qubit()

    validate(assert_unreachable_warning_emitted(test.compile_function))


def test_unreachable_copy(validate):
    @guppy
    def test() -> None:
        q = qubit()
        discard(q)
        if False:
            # This would be a linearity violation, but we don't complain since it's
            # unreachable:
            h(q)

    validate(assert_unreachable_warning_emitted(test.compile_function))


def test_if_false_emits_warning():
    """Statically unreachable branches should emit a single compiler warning."""

    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")

        @compile_guppy
        def test() -> int:
            if False:
                return 1
            return 0

    guppy_records = guppy_warning_records(records)
    assert len(guppy_records) == 1
    warning = guppy_records[0]
    assert warning.category is GuppyWarning
    assert warning.filename.endswith("test_unreachable.py")
    assert str(warning.message) == "Unreachable: This code is not reachable"


def test_dead_code_after_return_emits_warning():
    """Statements after an unconditional return should be reported as unreachable."""

    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")

        @compile_guppy
        def test() -> int:
            return 0
            x = 1
            return x

    guppy_records = guppy_warning_records(records)
    assert len(guppy_records) == 1
    warning = guppy_records[0]
    assert warning.category is GuppyWarning
    assert warning.filename.endswith("test_unreachable.py")
    assert str(warning.message) == "Unreachable: This code is not reachable"


def test_unreachable_warning_is_discarded_if_compilation_fails():
    """Warnings should not leak when unreachable code still contains a hard error."""

    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        with pytest.raises(GuppyError):

            @compile_guppy
            def test() -> int:
                if False:
                    return 1.0
                return 0

    guppy_records = guppy_warning_records(records)
    assert len(guppy_records) == 0
