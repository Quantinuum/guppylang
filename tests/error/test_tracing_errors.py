import pathlib
import pytest

from guppylang_internals.tracing.state import reset_state
from tests.error.util import run_error_test
from tests.conftest import experimental_features_enabled

path = pathlib.Path(__file__).parent.resolve() / "tracing_errors"
files = [
    x
    for x in path.iterdir()
    if x.is_file() and x.suffix == ".py" and x.name != "__init__.py"
]

# Turn paths into strings, otherwise pytest doesn't display the names
files = [str(f) for f in files]

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

    if needs_experimental_features:
        with experimental_features_enabled():
            run_error_test(file, capsys, snapshot)
    else:
        run_error_test(file, capsys, snapshot)
