from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.struct
class MyStruct:
    q: qubit


@guppy.declare
def use(q: qubit @owned) -> None: ...


@guppy
def test(s: MyStruct) -> None:
    use(s.q)


test.compile()
