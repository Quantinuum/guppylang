import pytest
from guppylang.decorator import expected_qubits, guppy, metadata


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
        match=(
            r"`daggered` in the `@guppy\.unitary` class `Foo` must be a guppy "
            r"function"
        ),
    ):

        @guppy.unitary
        class Foo:
            @guppy
            def __call__() -> None:
                pass

            @guppy.struct
            class daggered:
                value: int


def test_unitary_requires_guppy_call_method(use_experimental_features):
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
        match=(
            r"`controlled` in the `@guppy\.unitary` class `Foo` must be a guppy "
            r"function"
        ),
    ):

        @guppy.unitary
        class Foo:
            @guppy
            def __call__() -> None:
                pass

            def controlled() -> None:
                pass


@pytest.mark.parametrize("flag", ["unitary", "controllable", "daggerable"])
def test_unitary_custom_method_rejects_unitary_flags(flag, use_experimental_features):
    with pytest.raises(
        TypeError,
        match=(
            r"`daggered` in the `@guppy\.unitary` class `Foo` cannot set unitary "
            r"flags; only `__call__` can set them"
        ),
    ):

        @guppy.unitary
        class Foo:
            @guppy
            def __call__() -> None:
                pass

            @guppy(**{flag: True})
            def daggered() -> None:
                pass


def test_unitary_custom_method_rejects_expected_qubits(use_experimental_features):
    with pytest.raises(
        TypeError,
        match=(
            r"`controlled` in the `@guppy\.unitary` class `Foo` cannot use "
            r"`@expected_qubits`; only `__call__` can use it"
        ),
    ):

        @guppy.unitary
        class Foo:
            @guppy
            def __call__() -> None:
                pass

            @guppy
            @expected_qubits(2)
            def controlled() -> None:
                pass
