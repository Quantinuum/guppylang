from pathlib import Path

import pytest

from tests.error.util import run_error_test, collect_error_test_cases


files = collect_error_test_cases("array_errors")

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
    "non_array_subscript.py",
}

files = [
    pytest.param(file, marks=pytest.mark.skip(reason="The index bounds checking is currently disabled (https://github.com/Quantinuum/guppylang/issues/1669)."))
    if any(skipped_name in Path(file).name for skipped_name in skipped_files)
    else file
    for file in files
]


@pytest.mark.parametrize("file", files)
def test_array_errors(file, capsys, snapshot):
    run_error_test(file, capsys, snapshot)
