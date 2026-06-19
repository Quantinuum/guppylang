import pathlib

import pytest
from guppylang import guppy

from tests.error.util import run_error_test

path = pathlib.Path(__file__).parent.resolve() / "alias_errors"
files = [
    x
    for x in path.iterdir()
    if x.is_file() and x.suffix == ".py" and x.name != "__init__.py"
]

# Turn paths into strings, otherwise pytest doesn't display the names
files = [str(f) for f in files]


@pytest.mark.parametrize("file", files)
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
