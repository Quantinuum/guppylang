import pathlib
import pytest

from tests.error.util import run_error_test
from tests.conftest import experimental_features_enabled

path = pathlib.Path(__file__).parent.resolve() / "nested_errors"
files = [
    x
    for x in path.iterdir()
    if x.is_file() and x.suffix == ".py" and x.name != "__init__.py"
]

# Turn paths into strings, otherwise pytest doesn't display the names
files = [str(f) for f in files]


@pytest.mark.parametrize("file", files)
def test_nested_errors(file, capsys, snapshot):
    with experimental_features_enabled():
        run_error_test(file, capsys, snapshot)
