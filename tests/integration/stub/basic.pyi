"""Basic tests for generating Guppy stubs."""
from guppylang import guppy

@guppy.declare
def lib_func(x: int) -> int:
    ...

@guppy.declare(link_name='my.custom.link.name')
def lib_custom_link_name(x: int) -> int:
    ...

@guppy.declare(unitary=True)
def lib_unitary(x: int) -> int:
    ...

@guppy.declare(control=True, dagger=True)
def lib_multiple_modifiers(x: int) -> int:
    ...

@guppy.declare(unitary=True, link_name='my.custom.link.name')
def lib_multiple_kwargs(x: int) -> int:
    ...

@guppy.declare(max_qubits=2)
def lib_max_qubits(x: int) -> int:
    ...