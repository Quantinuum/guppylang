from guppylang.decorator import guppy
from guppylang.std.builtins import dagger
from guppylang.std.quantum import qubit, h


@guppy.struct
class MyStruct:
    q: qubit
    x: int


@guppy(daggerable=True)
def foo(s: MyStruct) -> None:
    h(s.q)


@guppy
def test(s: MyStruct) -> None:
    with dagger:
        foo(s)


test.compile_function()
