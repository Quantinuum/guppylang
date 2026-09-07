import pytest

from guppylang_internals.tracing.state import reset_state
from tests.error.util import run_error_test, collect_error_test_cases

files = collect_error_test_cases("tracing_errors")

# Snapshot tests that require experimental features.
tests_that_require_experimental_features = [
        "comptime_flags_nested_triple.py",
        "comptime_flags_nested_dagger_power.py",
        "comptime_flags_nested_power_control.py",
]
files_with_experimental_flag = [
    (file, any(case in file for case in tests_that_require_experimental_features))
    for file in files
]

@pytest.mark.parametrize("file,needs_experimental_features", files_with_experimental_flag)
def test_tracing_errors(file: str, needs_experimental_features: bool, capsys, snapshot):
    # Reset the tracing state by hand since the previous test catches the exception so
    # it's not reset
    reset_state()
    run_error_test(file, capsys, snapshot, needs_experimental_features)
