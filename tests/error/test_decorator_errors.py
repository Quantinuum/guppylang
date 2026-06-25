import pytest

from guppylang.decorator import guppy, metadata



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
        match="@metadata requires exactly 2 arguments, got 1",
    ):
        @guppy
        @metadata("key1")
        def foo() -> None:
            pass

    with pytest.raises(
        TypeError,
        match="@metadata requires exactly 2 arguments, got 0",
    ):
        @guppy.struct
        @metadata
        class MyStruct:
            x: int
            y: int
