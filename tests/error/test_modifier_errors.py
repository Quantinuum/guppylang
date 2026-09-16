import pytest

from tests.error.util import run_error_test, collect_error_test_cases


files = collect_error_test_cases("modifier_errors")

# Snapshot tests that require experimental features.
tests_that_require_experimental_features = [
    "captured_classical_modified.py",
    "captured_classical_modified_branch.py",
    "captured_classical_modified_multiple.py",
    "captured_classical_modified_nested.py",
    "captured_classical_modified_sequential.py",
    "captured_modifier_in_branch.py",
    "dagger_branch2.py",
    "dagger_loop3.py",
    "flags_nested.py",
    "flags_nested_combined_outer.py",
    "flags_nested_power_control.py",
    "flags_nested_triple.py",
    "flags_triple_dagger2.py",
    "power_arg_type.py",
    "power_arg_typecheck_inside.py",
    "power_many_arg.py",
    "power_no_arg.py",
]
files_with_experimental_flag = [
    (file, any(case in file for case in tests_that_require_experimental_features))
    for file in files
]

@pytest.mark.parametrize("file,needs_experimental_features", files_with_experimental_flag)
def test_modifier_errors(file: str, needs_experimental_features: bool, capsys, snapshot):
    run_error_test(file, capsys, snapshot, needs_experimental_features)
