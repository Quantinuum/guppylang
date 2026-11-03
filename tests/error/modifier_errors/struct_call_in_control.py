from typing import Generic

from guppylang import guppy
from guppylang.std.builtins import control
from guppylang.std.quantum import qubit

T = guppy.type_var("T")


@guppy.struct
class Inner(Generic[T]):
    q: qubit
    value: T


@guppy.struct
class Outer:
    inner: tuple[int, Inner[int]]


@guppy
def use(s: Outer) -> None:
    pass


@guppy
def main(c: qubit, s: Outer) -> None:
    with control(c):
        use(s)


main.compile_function()
