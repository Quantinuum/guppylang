import pytest

from guppylang import guppy


@pytest.mark.xfail
def test_hand(validate):
    """Regression test ensuring that pytest terminates, even if the Guppy compiler
    throws an error.

    See https://github.com/quantinuum/guppylang/issues/569
    """

    @guppy
    def test() -> int:
        return a  # Intentional use of an undefined variable  # noqa: F821

    validate(test.compile())
