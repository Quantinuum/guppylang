from tests.util import compile_guppy


@compile_guppy
def foo() -> None:
    xs = comptime([])
