import pytest

from tests.error.util import collect_error_test_cases, run_error_test

files = collect_error_test_cases("modifier_errors")

# Snapshot tests that require experimental features.
tests_that_require_experimental_features = [
    "dagger_loop3.py",
]
files_with_experimental_flag = [
    (file, any(case in file for case in tests_that_require_experimental_features))
    for file in files
]

@pytest.mark.parametrize("file,needs_experimental_features", files_with_experimental_flag)
def test_modifier_errors(file: str, needs_experimental_features: bool, capsys, snapshot):
    run_error_test(file, capsys, snapshot, needs_experimental_features)
