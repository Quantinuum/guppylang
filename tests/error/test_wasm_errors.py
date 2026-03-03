import pathlib
import pytest

from guppylang import guppy
from tests.error.util import run_error_test

path = pathlib.Path(__file__).parent.resolve() / "wasm_errors"
files = [
    x
    for x in path.iterdir()
    if x.is_file() and x.suffix == ".py" and x.name != "__init__.py"
]

# Turn paths into strings, otherwise pytest doesn't display the names
files = [str(f) for f in files]


@pytest.mark.parametrize("file", files)
def test_wasm_errors(file, capsys, snapshot):
    run_error_test(file, capsys, snapshot)
