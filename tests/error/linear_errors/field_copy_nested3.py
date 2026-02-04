from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.struct
class MyStruct1:
    x: "MyStruct2"


@guppy.struct
class MyStruct2:
    q: qubit


@guppy.declare
def use(s: MyStruct2 @owned) -> None: ...


@guppy
def foo(s: MyStruct1 @owned) -> qubit:
    use(s.x)
    return s.x.q


foo.compile()
