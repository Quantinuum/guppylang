import pytest

from tests.error.util import run_error_test, collect_error_test_cases


files = collect_error_test_cases(
    "output_errors",
    # TODO: Skip functional tests for now
    exclude=lambda path: path.is_file() and "functional" in path.name,
)

@pytest.mark.parametrize("file", files)
def test_misc_errors(file, capsys, snapshot):
    run_error_test(file, capsys, snapshot)
