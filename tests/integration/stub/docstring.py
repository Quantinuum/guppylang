"""Tests for inclusion of docstrings in the stub files. This module-level docstring
should be included."""

from guppylang import guppy


@guppy
def lib_docstring(x: int) -> int:
    """A docstring for this wonderful function, that is included in the stubs."""
    return x


@guppy
def lib_docstring_multiline(x: int) -> int:
    """A much longer docstring for this other wonderful function, which we should
    include in the stubs regardless of what is customary and what is not."""
    return x
