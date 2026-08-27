import pytest

from tests.error.util import run_error_test, collect_error_test_cases

files = collect_error_test_cases(
    "type_errors",
    # TODO: Skip functional tests for now
    exclude=lambda path: path.is_file() and "functional" in path.name,
)

# Snapshot tests that require experimental features.
tests_that_require_experimental_features = [
    "unitary_function_bad_method1.py",
    "unitary_function_bad_method2.py",
    "unitary_function_call_wrong.py",
    "unitary_function_return_error.py",
    "unpack_non_static.py",
]
files_with_experimental_flag = [
    (file, any(case in file for case in tests_that_require_experimental_features))
    for file in files
]

@pytest.mark.parametrize("file,needs_experimental_features", files_with_experimental_flag)
def test_type_errors(file: str, needs_experimental_features: bool, capsys, snapshot):
    run_error_test(file, capsys, snapshot, needs_experimental_features)
