from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.enum
class MyEnum:
    VariantA = {"q": qubit}  # noqa: RUF012


@guppy.declare
def use(s: MyEnum @owned) -> bool: ... # pyright: ignore[reportInvalidTypeForm]


@guppy
def foo(b: bool) -> bool:
    s = MyEnum.VariantA(qubit())
    if b:
        return use(s)
    return False


foo.compile()
