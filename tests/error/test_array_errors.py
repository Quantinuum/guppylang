import pathlib
import pytest

from tests.error.util import run_error_test

path = pathlib.Path(__file__).parent.resolve() / "array_errors"
files = [
    x
    for x in path.iterdir()
    if x.is_file() and x.suffix == ".py" and x.name != "__init__.py"
]

skipped_files = {
    "array_index_equal_size.py",
    "array_index_get.py",
    "array_index_is_borrowed.py",
    "array_index_negative_oob.py",
    "array_index_nested_array_inner.py",
    "array_index_nested_array_outer.py",
    "array_index_positive_oob.py",
    "array_index_put.py",
    "array_index_set.py",
    "array_index_take.py",
}

# Turn paths into strings, otherwise pytest doesn't display the names
files = [
    pytest.param(str(f), marks=pytest.mark.skip(reason="The index bounds checking is currently disabled (https://github.com/Quantinuum/guppylang/issues/1669)."))
    if f.name in skipped_files
    else str(f)
    for f in files
]


@pytest.mark.parametrize("file", files)
def test_array_errors(file, capsys, snapshot):
    run_error_test(file, capsys, snapshot)
