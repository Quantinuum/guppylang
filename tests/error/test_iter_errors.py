import pytest

from tests.error.util import run_error_test, collect_error_test_cases


@pytest.mark.parametrize("file", collect_error_test_cases("iter_errors"))
def test_iter_errors(file, capsys, snapshot):
    run_error_test(file, capsys, snapshot)
