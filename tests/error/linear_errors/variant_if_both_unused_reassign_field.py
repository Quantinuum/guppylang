from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.enum
class MyEnum:
    VariantA = {"q": qubit}  # noqa: RUF012


@guppy
def foo(b: bool, s: MyEnum @owned) -> MyEnum:
    if b:
        s = MyEnum.VariantA(qubit())
    else:
        s = MyEnum.VariantA(qubit())
    s = MyEnum.VariantA(qubit())
    return s


foo.compile()
