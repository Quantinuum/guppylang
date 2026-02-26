"""Basic tests for generating Guppy stubs."""
from guppylang import guppy

@guppy.declare
def lib_func(x: int) -> int:
    ...