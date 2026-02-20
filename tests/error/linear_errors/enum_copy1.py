from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.enum
class MyEnum:
    VariantA = {"q": qubit}  # noqa: RUF012


@guppy
def foo(s: MyEnum @owned) -> tuple[MyEnum, MyEnum]:
    t = s
    return s, t


foo.compile()
