# ruff: noqa: RUF059

from tests.util import compile_guppy


@compile_guppy
def no_return_unpack_condition(t: tuple[bool, bool]) -> int:
    a, b = t
    if a:
        return 0
