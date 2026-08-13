import pytest

from guppylang.decorator import guppy, metadata
from guppylang_internals.error import GuppyError


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


def test_unitary_custom_method_must_be_guppy_function(use_experimental_features):
    with pytest.raises(
        TypeError,
        match=r"`daggered` in the `@guppy\.unitary` class `Foo` must be a guppy function",
    ):
        @guppy.unitary
        class Foo:
            @guppy
            def __call__() -> None:
                pass

            @guppy.struct
            class daggered:
                value: int


def test_unitary_rejects_keyword_arguments():
    with pytest.raises(
        TypeError,
        match=r"does not accept keyword arguments.*`__call__` method",
    ):
        @guppy.unitary(daggerable=True)
        class Foo:
            pass


def test_unitary_rejects_unrecognised_guppy_method(use_experimental_features):
    with pytest.raises(
        TypeError,
        match=r"Only guppy function named .* are allowed .* Found `other`",
    ):
        @guppy.unitary
        class Foo:
            @guppy
            def __call__() -> None:
                pass

            @guppy
            def other() -> None:
                pass


def test_unitary_custom_method_requires_guppy_decorator(use_experimental_features):
    with pytest.raises(
        TypeError,
        match=r"`controlled` in the `@guppy\.unitary` class `Foo` must be a guppy function",
    ):
        @guppy.unitary
        class Foo:
            @guppy
            def __call__() -> None:
                pass

            def controlled() -> None:
                pass
