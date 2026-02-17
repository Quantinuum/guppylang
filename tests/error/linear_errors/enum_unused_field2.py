from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.enum
class MyEnum1:
    VariantA = {"x": "MyEnum2", "y": int}  # noqa: RUF012


@guppy.enum
class MyEnum2:
    VariantA = {"q1": qubit, "q2": qubit}  # noqa: RUF012


@guppy
def foo(s: MyEnum1 @owned) -> int:
    return 0


foo.compile()
