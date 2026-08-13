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
    "custom_controllable_daggered_missing_ctrl_daggered.py",
    "custom_control_decorator_constraint.py",
    "custom_control_invalid_controls.py",
    "custom_control_missing_controls.py",
    "custom_control_missing_type_param.py",
    "custom_control_owned_controls.py",
    "custom_control_signature.py",
    "custom_ctrl_daggered_missing_support.py",
    "custom_ctrl_daggered_signature.py",
    "custom_daggerable_controlled_missing_ctrl_daggered.py",
    "custom_dagger_decorator_constraint.py",
    "custom_dagger_ownership_signature.py",
    "custom_dagger_signature.py",
    "custom_modified_missing1.py",
    "custom_modified_missing2.py",
    "custom_modified_missing3.py",
    "custom_modifiers_missing_ctrl_daggered.py",
    "custom_unitary_higher_order_requires_dagger.py",
    "custom_unitary_higher_order_requires_unitary.py",
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
    run_error_test(file, capsys, snapshot, needs_experimental_features)
