from guppylang.decorator import guppy
from guppylang.std.builtins import control, dagger, power
from guppylang.std.quantum import discard, qubit



@guppy.comptime(control=True, power=True)
def foo(q: qubit) -> None:
    pass

@guppy
def main() -> None:
    q = qubit()
    c2 = qubit()
    with dagger():
        with power(2), dagger:
            with control(c2), dagger:
                foo(q)
    
    discard(q)
    discard(c2)
                
main.check()
