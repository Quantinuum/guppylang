import pytest

from hugr import ops, val

from guppylang.decorator import guppy
from guppylang_internals.error import GuppyError
from guppylang_internals.checker.cfg_checker import VarMaybeNotDefinedError


def test_extern_float(validate):
    ext = guppy._extern("ext", ty="float")

    @guppy
    def main() -> float:
        return ext + ext

    package = main.compile_function()
    validate(package)

    hg = package.modules[0]
    [c] = [data.op for n, data in hg.nodes() if isinstance(data.op, ops.Const)]
    assert isinstance(c.val, val.Extension)
    assert c.val.val["symbol"] == "ext"


def test_extern_alt_symbol(validate):
    ext = guppy._extern("ext", ty="int", symbol="foo")

    @guppy
    def main() -> int:
        return ext

    package = main.compile_function()
    validate(package)

    hg = package.modules[0]
    [c] = [data.op for n, data in hg.nodes() if isinstance(data.op, ops.Const)]
    assert isinstance(c.val, val.Extension)
    assert c.val.val["symbol"] == "foo"


def test_extern_tuple(validate):
    ext = guppy._extern("ext", ty="tuple[int, float]")

    @guppy
    def main() -> float:
        x, y = ext
        return x + y

    validate(main.compile_function())


# See https://github.com/quantinuum/guppylang/issues/827
def test_extern_conditional_assign():
    x = guppy._extern("x", ty="int")

    @guppy
    def main(b: bool) -> int:
        if b:
            x = 4
        return x

    with pytest.raises(
        GuppyError,
        check=lambda e: (
            isinstance(e.error, VarMaybeNotDefinedError)
            and "Variable not defined" in e.error.title
            and "x" == e.error.var
        ),
    ):
        main.compile_function()
