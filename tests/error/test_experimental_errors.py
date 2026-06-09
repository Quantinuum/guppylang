import pathlib
import pytest

from guppylang.experimental import are_experimental_features_enabled, set_experimental_features_enabled
from tests.error.util import run_error_test

path = pathlib.Path(__file__).parent.resolve() / "experimental_errors"
files = [
    x
    for x in path.iterdir()
    if x.is_file() and x.suffix == ".py" and x.name != "__init__.py"
]

# Turn paths into strings, otherwise pytest doesn't display the names
files = [str(f) for f in files]


@pytest.mark.parametrize("file", files)
def test_experimental_errors(file, capsys, snapshot):
    original = are_experimental_features_enabled()
    set_experimental_features_enabled(False)

    run_error_test(file, capsys, snapshot)

    set_experimental_features_enabled(original)
