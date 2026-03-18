from guppylang import qubit
from guppylang.decorator import guppy
from guppylang_internals.decorator import custom_function
from pytket import Circuit


def test_func_def():
    @guppy
    def func_def() -> None:
        return

    assert not func_def.is_decl


def test_func_decl():
    @guppy.declare
    def func_decl() -> None: ...

    assert func_decl.is_decl


def test_func_overload():
    @guppy.declare
    def variant_1() -> None: ...
    @guppy.declare
    def variant_2() -> None: ...

    @guppy.overload(variant_1, variant_2)
    def func_overload() -> None: ...

    assert not func_overload.is_decl


def test_pytket_func():
    circ = Circuit(1)
    circ.H(0)

    @guppy.pytket(circ)
    def guppy_circ(q1: qubit) -> None: ...

    assert not guppy_circ.is_decl


def test_load_pytket_func():
    circ = Circuit(1)
    circ.H(0)

    guppy_circ = guppy.load_pytket("circ", circ)

    assert not guppy_circ.is_decl


def test_custom_func():
    @custom_function()
    def custom(x): ...

    assert not custom.is_decl
