from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.struct
class MyStruct:
    q: qubit

@guppy
def test(q: qubit) -> MyStruct:
    return MyStruct(q)


test.compile()
