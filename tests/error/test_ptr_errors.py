import pytest

from tests.error.util import collect_error_test_cases, run_error_test


@pytest.mark.parametrize("file", collect_error_test_cases("ptr_errors"))
def test_ptr_errors(file, capsys, snapshot):
    run_error_test(file, capsys, snapshot)
