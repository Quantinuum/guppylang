"""Basic tests for generating Guppy stubs."""
from guppylang import guppy

@guppy.declare
def lib_func(x: int) -> int:
    ...

@guppy.declare
def lib_func_using_import_in_body(x: int) -> int:
    ...

@guppy.declare
def lib_func_using_import_in_signature(x: array[int, 3]) -> None:
    ...