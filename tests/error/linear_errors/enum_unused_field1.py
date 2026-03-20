from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.enum
class MyEnum:
    VariantA = {"q": qubit, "x": int}  # noqa: RUF012


@guppy
def foo(s: MyEnum @owned) -> int:
    return 42


foo.compile()
