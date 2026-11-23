from guppylang.decorator import guppy
from guppylang.std.quantum import qubit, h


@guppy.struct
class MyStruct:
    q: qubit
    x: int


@guppy(daggerable=True)
def foo(s: MyStruct) -> None:
    h(s.q)


@guppy(daggerable=True)
def test(s: MyStruct) -> None:
    foo(s)


test.compile_function()
