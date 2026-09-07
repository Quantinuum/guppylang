from guppylang import guppy, qubit
from guppylang.std.builtins import panic, control
from guppylang.std.quantum import measure

@guppy
def test(q: qubit) -> None:
    pass

@guppy
def bar() -> None:
    q = qubit()
    qq = qubit()
    with control(q):
        panic("a", test(qq))

    measure(q)
    measure(qq)

bar.compile_function()