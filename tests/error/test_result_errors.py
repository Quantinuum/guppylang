import pathlib
import pytest

from tests.error.util import run_error_test

path = pathlib.Path(__file__).parent.resolve() / "result_errors"
files = [
    x
    for x in path.iterdir()
    if x.is_file() and x.suffix == ".py" and x.name != "__init__.py"
]

# TODO: Skip functional tests for now
files = [f for f in files if "functional" not in f.name]

# Turn paths into strings, otherwise pytest doesn't display the names
files = [str(f) for f in files]


@pytest.mark.parametrize("file", files)
def test_misc_errors(file, capsys, snapshot):
    run_error_test(file, capsys, snapshot)
