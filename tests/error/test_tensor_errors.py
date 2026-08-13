import pytest

from tests.error.util import run_error_test, collect_error_test_cases
from tests.conftest import experimental_features_enabled


@pytest.mark.parametrize("file", collect_error_test_cases("tensor_errors"))
def test_type_errors(file, capsys, snapshot):
    with experimental_features_enabled():
        run_error_test(file, capsys, snapshot)
