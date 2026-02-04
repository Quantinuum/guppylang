"""Dummy module used in `test_imports.py`"""

from guppylang import guppy
from guppylang_internals.decorator import hugr_op
from guppylang_internals.std._internal.util import unsupported_op


@guppy
def f(x: bool) -> bool:
    return not x


@hugr_op(unsupported_op("h"))
def h() -> int: ...


@guppy.struct
class MyType:
    x: int

    @guppy
    def __pos__(self: "MyType") -> "MyType":
        return self
