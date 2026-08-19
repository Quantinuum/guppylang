import pytest

from tests.error.util import run_error_test, collect_error_test_cases


files = collect_error_test_cases(
    "errors_on_usage",
    # TODO: Skip functional tests for now
    exclude=lambda path: path.is_file() and "functional" in path.name,
)

# Snapshot tests that require experimental features.
tests_that_require_experimental_features = [
        "for_new_var.py",
        "for_target.py",
        "for_target_type_change.py",
        "for_type_change.py",
        "var_in_modifier1.py",
        "var_in_modifier2.py",
        "var_in_modifier3.py",
        "var_in_modifier4.py",
        "var_undefined_before_modifier1.py",
        "var_undefined_before_modifier2.py",
]
files_with_experimental_flag = [
    (file, any(case in file for case in tests_that_require_experimental_features))
    for file in files
]

@pytest.mark.parametrize("file,needs_experimental_features", files_with_experimental_flag)
def test_errors_on_usage(file: str, needs_experimental_features: bool, capsys, snapshot):
    run_error_test(file, capsys, snapshot, needs_experimental_features)
