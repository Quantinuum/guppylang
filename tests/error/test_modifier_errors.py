import pytest

from tests.error.util import run_error_test, collect_error_test_cases


files = collect_error_test_cases("modifier_errors")

# No tests require experimental features.
@pytest.mark.parametrize("file,needs_experimental_features", [])
def test_modifier_errors(file: str, needs_experimental_features: bool, capsys, snapshot):
    run_error_test(file, capsys, snapshot, needs_experimental_features)
