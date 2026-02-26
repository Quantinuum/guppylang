"""Basic tests for generating Guppy stubs."""

from guppylang import guppy
from ast import Module  # noqa: F401, this should be removed in the stub


@guppy
def lib_func(x: int) -> int:
    return x
