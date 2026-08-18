import pytest
from guppylang import guppy
from guppylang.std.quantum import qubit

from tests.error.util import run_error_test, collect_error_test_cases


@pytest.mark.parametrize("file", collect_error_test_cases("overload_errors"))
def test_overload_errors(file, capsys, snapshot):
    run_error_test(file, capsys, snapshot)


def test_not_enough_overloads():
    @guppy.declare
    def foo() -> None: ...

    with pytest.raises(ValueError, match="Overload requires at least two functions"):
        @guppy.overload()
        def overloaded(): ...

    with pytest.raises(ValueError, match="Overload requires at least two functions"):
        @guppy.overload
        def overloaded(): ...

    with pytest.raises(ValueError, match="Overload requires at least two functions"):
        @guppy.overload(foo)
        def overloaded(): ...


def test_non_guppy_overload():
    @guppy.declare
    def foo() -> None: ...

    with pytest.raises(TypeError, match="Not a Guppy definition: 42"):
        @guppy.overload(foo, 42)
        def overloaded(): ...


def test_non_function_overload():
    @guppy.declare
    def foo() -> None: ...

    with pytest.raises(
        TypeError, match="Not a Guppy function definition: type `qubit`"
    ):
        @guppy.overload(foo, qubit)
        def overloaded(): ...
