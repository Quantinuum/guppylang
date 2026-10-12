import pytest
from guppylang import guppy

from tests.error.util import run_error_test, collect_error_test_cases


@pytest.mark.parametrize("file", collect_error_test_cases("alias_errors"))
def test_alias_errors(file, capsys, snapshot):
    run_error_test(file, capsys, snapshot)


def test_type_alias_bad_type_syntax():
    with pytest.raises(SyntaxError, match="Not a valid Guppy type: `foo bar`"):
        guppy.type_alias("MyAlias", "foo bar")


def test_type_alias_invalid_param():
    with pytest.raises(
        TypeError,
        match="type_alias params must be type variables created with",
    ):
        guppy.type_alias("MyAlias", "int", params=["not a type var"])


def test_type_alias_param_string_instead_of_var():
    # Passing a type var name as a plain string (instead of the var object) is rejected.
    T = guppy.type_var("T")  # noqa: F841
    with pytest.raises(
        TypeError,
        match="type_alias params must be type variables created with",
    ):
        guppy.type_alias("MyAlias", "int", params=["T"])


def test_type_alias_param_not_a_param_def():
    # A `GuppyDefinition` that isn't a type variable (e.g. a struct) is rejected.
    @guppy.struct
    class SomeStruct:
        x: int

    with pytest.raises(
        TypeError,
        match="type_alias params must be type variables created with",
    ):
        guppy.type_alias("MyAlias", "int", params=[SomeStruct])
