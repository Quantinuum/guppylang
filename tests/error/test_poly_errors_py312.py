import pytest

from tests.error.util import run_error_test, collect_error_test_cases


@pytest.mark.parametrize("file", collect_error_test_cases("poly_errors_py312"))
def test_poly_errors_py312(file, capsys, snapshot):
    run_error_test(file, capsys, snapshot)
