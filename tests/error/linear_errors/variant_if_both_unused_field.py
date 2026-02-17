from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.enum
class MyEnum:
    VariantA = {"q": qubit}  # noqa: RUF012


@guppy
def foo(b: bool) -> int:
    if b:
        s = MyEnum.VariantA(qubit())
    else:
        s = MyEnum.VariantA(qubit())
    return 42


foo.compile()
