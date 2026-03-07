from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.enum
class MyEnum1:
    VariantA = {"q": qubit, "x": "MyEnum2"}  # noqa: RUF012


@guppy.enum
class MyEnum2:
    VariantA = {"q": qubit}  # noqa: RUF012


@guppy.declare
def use(s: MyEnum1 @owned) -> None: ...


@guppy
def foo(s: MyEnum1 @owned) -> MyEnum1:
    t = s
    use(t)
    return s


foo.compile()
