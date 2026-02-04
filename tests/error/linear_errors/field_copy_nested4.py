from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit, measure


@guppy.struct
class MyStruct1:
    x: "MyStruct2"


@guppy.struct
class MyStruct2:
    q: qubit


@guppy.declare
def use(s: MyStruct1 @owned) -> None: ...


@guppy
def foo(s: MyStruct1 @owned) -> MyStruct1:
    use(s)
    return s


foo.compile()
