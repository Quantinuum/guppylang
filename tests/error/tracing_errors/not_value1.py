from hugr import tys
from guppylang import guppy
from guppylang_internals.decorator import custom_type


@custom_type(tys.Tuple())
class T:
    pass


@guppy.declare
def foo(x: T) -> None: ...


@guppy.comptime
def test() -> None:
    foo(T)


test.compile()
