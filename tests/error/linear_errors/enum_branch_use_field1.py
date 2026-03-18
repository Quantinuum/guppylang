from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.enum
class MyEnum:
    VariantA = {"q1": qubit, "q2": qubit}  # noqa: RUF012


@guppy.declare
def use(s: MyEnum @owned) -> None: ... # pyright: ignore[reportInvalidTypeForm]


@guppy
def foo(b: bool, s: MyEnum @owned) -> MyEnum: # pyright: ignore[reportInvalidTypeForm]
    if b:
        use(s)
    return s


foo.compile()
