"""Basic tests for generating Guppy stubs."""

from guppylang import guppy


@guppy
def lib_func(x: int) -> int:
    return x


@guppy(link_name="my.custom.link.name")
def lib_custom_link_name(x: int) -> int:
    return x


@guppy(unitary=True)
def lib_unitary(x: int) -> int:
    return x


@guppy(control=True, dagger=True)
def lib_multiple_modifiers(x: int) -> int:
    return x


@guppy(unitary=True, link_name="my.custom.link.name")
def lib_multiple_kwargs(x: int) -> int:
    return x


@guppy(max_qubits=2)
def lib_max_qubits(x: int) -> int:
    return x
