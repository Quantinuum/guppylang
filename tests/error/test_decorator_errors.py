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


def test_unitary_requires_guppy_call_method():
    with pytest.raises(
        TypeError,
        match=(
            r"The `@guppy\.unitary` class `Foo` requires a `@guppy` annotated "
            r"`__call__` method"
        ),
    ):

        @guppy.unitary
        class Foo:
            pass


def test_unitary_requires_class():
    with pytest.raises(
        TypeError,
        match=r"`@guppy\.unitary` must be applied directly to a class",
    ):

        @guppy.unitary
        def foo() -> None:
            pass

    with pytest.raises(
        TypeError,
        match=r"`@guppy\.unitary` must be applied directly to a class",
    ):
        guppy.unitary()


def test_unitary_rejects_keyword_arguments():
    with pytest.raises(
        TypeError,
        match=r"does not accept keyword arguments.*`__call__` method",
    ):

        @guppy.unitary(daggerable=True)
        class Foo:
            pass
