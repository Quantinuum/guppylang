from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.enum
class MyEnum1:
    VariantA = {"x": "MyEnum2"}  # noqa: RUF012


@guppy.enum
class MyEnum2:
    VariantA = {"q1": qubit, "q2": qubit}  # noqa: RUF012


@guppy.declare
def use(s: MyEnum1 @owned) -> None: ... # pyright: ignore[reportInvalidTypeForm]


@guppy
def foo() -> MyEnum1:
    s = MyEnum1.VariantA(MyEnum2.VariantA(qubit(), qubit()))
    use(s)
    return s


foo.compile()
