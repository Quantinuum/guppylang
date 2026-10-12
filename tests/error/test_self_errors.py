import pytest

from guppylang import guppy
from tests.error.util import run_error_test, collect_error_test_cases


@pytest.mark.parametrize("file", collect_error_test_cases("self_errors"))
def test_misc_errors(file, capsys, snapshot):
    run_error_test(file, capsys, snapshot)


def test_extern_bad_type_syntax():
    with pytest.raises(SyntaxError, match="Not a valid Guppy type: `foo bar`"):
        guppy._extern(name="x", ty="foo bar")
