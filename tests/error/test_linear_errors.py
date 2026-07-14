import pathlib
import pytest

from tests.error.util import run_error_test
from tests.conftest import experimental_features_enabled

path = pathlib.Path(__file__).parent.resolve() / "linear_errors"
files = [
    x
    for x in path.iterdir()
    if x.is_file() and x.suffix == ".py" and x.name != "__init__.py"
]

# TODO: Skip functional tests for now
files = [f for f in files if "functional" not in f.name]

# Turn paths into strings, otherwise pytest doesn't display the names
files = [str(f) for f in files]

# Snapshot tests that require experimental features.
tests_that_require_experimental_features = [
    "captured_var_inout_own1.py",
    "captured_var_inout_own2.py",
    "for_break.py",
    "for_return.py",
]
files_with_experimental_flag = [
    (file, any(case in file for case in tests_that_require_experimental_features))
    for file in files
]

@pytest.mark.parametrize("file,needs_experimental_features", files_with_experimental_flag)
def test_linear_errors(file: str, needs_experimental_features: bool, capsys, snapshot):
    if needs_experimental_features:
        with experimental_features_enabled():
            run_error_test(file, capsys, snapshot)
    else:
        run_error_test(file, capsys, snapshot)
