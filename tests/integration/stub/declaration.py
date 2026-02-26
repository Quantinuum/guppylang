"""Tests that Guppy stubs can be generated for function declarations."""

from guppylang import guppy


@guppy.declare
def lib_decl(x: int) -> int: ...


@guppy.declare(link_name="my.custom.link.name")
def lib_decl_custom_link_name(x: int) -> int: ...
