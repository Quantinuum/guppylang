from guppylang.decorator import guppy
from guppylang.std.quantum import qubit, measure


@guppy.struct
class MyStruct:
    q: qubit


@guppy
def foo(b: bool) -> bool:
    s = MyStruct(qubit())
    if b:
        return measure(s.q)
    return False


foo.compile()
