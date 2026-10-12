import pytest

from guppylang.experimental import are_experimental_features_enabled, set_experimental_features_enabled
from tests.error.util import run_error_test, collect_error_test_cases


@pytest.mark.parametrize("file", collect_error_test_cases("experimental_errors"))
def test_experimental_errors(file, capsys, snapshot):
    original = are_experimental_features_enabled()
    set_experimental_features_enabled(False)

    run_error_test(file, capsys, snapshot)

    set_experimental_features_enabled(original)
