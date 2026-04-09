from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.enum
class MyEnum:
    VariantA = {"q1": qubit, "q2": qubit}  # noqa: RUF012


@guppy
def foo() -> qubit:
    e = MyEnum.VariantA(qubit(), qubit())
    return qubit()


foo.compile()
