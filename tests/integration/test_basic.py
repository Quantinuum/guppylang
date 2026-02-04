import pytest
from hugr import ops

from guppylang.decorator import guppy
from tests.util import compile_guppy


def test_id(validate):
    @compile_guppy
    def identity(x: int) -> int:
        return x

    validate(identity)


def test_void(validate):
    @compile_guppy
    def void() -> None:
        return

    validate(void)


def test_copy(validate):
    @compile_guppy
    def copy(x: int) -> tuple[int, int]:
        return x, x

    validate(copy)


def test_discard(validate):
    @compile_guppy
    def discard(x: int) -> None:
        return

    validate(discard)


def test_implicit_return(validate):
    @compile_guppy
    def ret() -> None:
        pass

    validate(ret)


def test_assign(validate):
    @compile_guppy
    def foo(x: bool) -> bool:
        y = x
        return y

    validate(foo)


def test_assign_expr(validate):
    @compile_guppy
    def foo(x: bool) -> bool:
        (y := x)
        return y

    validate(foo)


def test_func_decl_name():
    @guppy.declare
    def func_name() -> None: ...

    hugr = func_name.compile_function().modules[0]
    [def_op] = [
        data.op for n, data in hugr.nodes() if isinstance(data.op, ops.FuncDecl)
    ]
    assert isinstance(def_op, ops.FuncDecl)
    assert def_op.f_name == "func_name"


@pytest.mark.xfail(reason="Caching not implemented yet")
def test_compile_again():
    @guppy
    def identity(x: int) -> int:
        return x

    hugr = identity.compile_function().module

    # Compiling again should return the same Hugr
    assert hugr is identity.compile_function()
