import pytest

from guppylang import guppy
from tests.error.util import run_error_test, collect_error_test_cases


files = collect_error_test_cases(
    "misc_errors",
    # TODO: Skip functional tests for now
    exclude=lambda path: path.is_file() and "functional" in path.name,
)


@pytest.mark.parametrize("file", files)
def test_misc_errors(file, capsys, snapshot):
    run_error_test(file, capsys, snapshot)


def test_extern_bad_type_syntax():
    with pytest.raises(SyntaxError, match="Not a valid Guppy type: `foo bar`"):
        guppy._extern(name="x", ty="foo bar")


def test_bad_kwargs():
    with pytest.raises(TypeError, match="Unknown keyword argument: `foo`"):
        @guppy(foo=42)
        def main() -> None:
            pass
