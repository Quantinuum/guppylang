
from guppylang import guppy, qubit
from guppylang.std.builtins import owned, power, control
from guppylang.std.quantum import measure


@guppy
def main() -> int:
    q = qubit()
    if True:
        x = 3
    with power(3): 
        b = 4
        with control(q):
            a = 4
    
    measure(q)

    return a



main.check()