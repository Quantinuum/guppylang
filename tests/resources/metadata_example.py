"""File used to test the filename table in debug info metadata."""

from guppylang import guppy


@guppy
def bar() -> None:
    # Leave white space to check scope_line is set correctly.

    pass


@guppy.declare
def baz() -> None: ...
