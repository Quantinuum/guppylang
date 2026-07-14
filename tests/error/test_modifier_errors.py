import pathlib
import pytest

from tests.error.util import run_error_test
from tests.conftest import experimental_features_enabled

path = pathlib.Path(__file__).parent.resolve() / "modifier_errors"
files = [
    x
    for x in path.iterdir()
    if x.is_file() and x.suffix == ".py" and x.name != "__init__.py"
]

# Turn paths into strings, otherwise pytest doesn't display the names
files = [str(f) for f in files]

# Snapshot tests that require experimental features.
tests_that_require_experimental_features = [
    "dagger_loop3.py",
    "power_arg_typecheck_inside.py",
    "flags_nested_combined_outer.py",
    "captured_classical_modified_nested.py",
    "captured_classical_modified.py",
    "captured_modifier_in_branch.py",
    "dagger_branch2.py",
    "captured_classical_modified_multiple.py",
    "flags_nested.py",
    "power_arg_type.py",
    "captured_classical_modified_sequential.py",
    "captured_classical_modified_branch.py",
    "flags_triple_dagger2.py",
    "flags_nested_triple.py",
    "flags_nested_power_control.py",
    "power_many_arg.py",
    "power_no_arg.py",
]
files_with_experimental_flag = [
    (file, any(case in file for case in tests_that_require_experimental_features))
    for file in files
]

@pytest.mark.parametrize("file,needs_experimental_features", files_with_experimental_flag)
def test_modifier_errors(file: str, needs_experimental_features: bool, capsys, snapshot):
    if needs_experimental_features:
        with experimental_features_enabled():
            run_error_test(file, capsys, snapshot)
    else:
        run_error_test(file, capsys, snapshot)
