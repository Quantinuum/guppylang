import pathlib
import pytest
import sys

from guppylang import guppy
from tests.error.util import run_error_test

path = pathlib.Path(__file__).parent.resolve() / "self_errors"
files = [
    x
    for x in path.iterdir()
    if x.is_file() and x.suffix == ".py" and x.name != "__init__.py"
]

if sys.version_info < (3, 12):
    # Filter out tests that require Python >= 3.12
    files = [file for file in files if "py312" not in file.name]

# Turn paths into strings, otherwise pytest doesn't display the names
files = [str(f) for f in files]


@pytest.mark.parametrize("file", files)
def test_misc_errors(file, capsys, snapshot):
    run_error_test(file, capsys, snapshot)


def test_extern_bad_type_syntax():
    with pytest.raises(SyntaxError, match="Not a valid Guppy type: `foo bar`"):
        guppy._extern(name="x", ty="foo bar")
