import pytest
from guppylang_internals.tracing.state import reset_state

from tests.error.util import collect_error_test_cases, run_error_test

files = collect_error_test_cases("tracing_errors")


@pytest.mark.parametrize("file", files)
def test_tracing_errors(file: str, capsys, snapshot):
    # Reset the tracing state by hand since the previous test catches the exception so
    # it's not reset
    reset_state()
    run_error_test(file, capsys, snapshot)
