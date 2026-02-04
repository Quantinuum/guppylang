from guppylang import guppy
from guppylang_internals.decorator import extend_type
from tests.integration.modules.mod_a import f, MyType


@guppy.declare
def g() -> MyType: ...


@guppy
def h(x: int) -> int:
    return f(x)


# Extend type defined in module A
@extend_type(MyType)
class _:
    @guppy
    def __int__(self: "MyType") -> int:
        return 0
