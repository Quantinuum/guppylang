from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.declare
def foo(q: qubit) -> None: ...


@guppy.enum
class MyImmutableContainer:
    Var = {"q": qubit}

    @guppy.declare
    def __getitem__(self: "MyImmutableContainer", idx: int) -> qubit: ...


@guppy
def test(c: MyImmutableContainer) -> MyImmutableContainer:
    foo(c[0])
    return c

test.check()