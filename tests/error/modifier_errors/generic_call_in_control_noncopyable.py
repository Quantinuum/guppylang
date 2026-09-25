from guppylang import guppy, qubit
from guppylang.std.builtins import control
from guppylang.std.quantum import discard


@guppy
def generic_function[T](x: T) -> None:
    pass


@guppy
def controlled_generic_call[T](x: T) -> None:
    q = qubit()

    with control(q):
        generic_function(x)

    discard(q)


@guppy
def main() -> None:
    q = qubit()
    controlled_generic_call(q)
    discard(q)


main.compile_function()