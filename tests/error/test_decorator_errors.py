import pytest
from guppylang.decorator import guppy, metadata

from tests.error.util import collect_error_test_cases, run_error_test


def test_metadata_decorator_position():
    with pytest.raises(
        TypeError,
        match="@metadata must be placed below the @guppy decorator, not above it",
    ):

        @metadata("key", "value")
        @guppy
        def foo() -> None:
            pass


def test_metadata_decorator_arguments():
    with pytest.raises(
        TypeError,
        match=r"metadata\(\) missing 1 required positional argument: 'value'",
    ):

        @guppy
        @metadata("key1")
        def foo() -> None:
            pass

    with pytest.raises(
        TypeError,
        match=r"metadata\(\) missing 1 required positional argument: 'value'",
    ):

        @guppy.struct
        @metadata
        class MyStruct:
            x: int
            y: int


@pytest.mark.parametrize("file", collect_error_test_cases("decorator_errors"))
def test_decorator_errors(file, capsys, snapshot):
    run_error_test(file, capsys, snapshot)
