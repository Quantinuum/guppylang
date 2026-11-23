from typing import Generic

from guppylang import guppy
from guppylang.std.builtins import control
from guppylang.std.quantum import qubit

T = guppy.type_var("T")


@guppy.enum
class E(Generic[T]):
    Classical = {"value": T}
    Quantum = {"q": qubit}


@guppy
def use(e: E[int]) -> None:
    pass


@guppy
def main(c: qubit, e: E[int]) -> None:
    with control(c):
        use(e)


main.compile_function()
