"""Basic tests for generating Guppy stubs."""
from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.angles import angle

@guppy.declare
def lib_func(x: int) -> int:
    ...

@guppy.declare
def lib_func_using_import_in_body(x: int) -> int:
    ...

@guppy.declare
def lib_func_using_import_in_args(x: angle) -> None:
    ...

@guppy.declare
def lib_func_using_import_in_return() -> array[int, 3]:
    ...