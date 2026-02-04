from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned
from guppylang.std.quantum import qubit


@guppy.declare
def foo(qs: array[qubit, 42] @owned, q: qubit) -> array[qubit, 42]: ...


@guppy
def main(qs: array[qubit, 42] @owned) -> array[qubit, 42]:
    return foo(qs, qs[0])


main.compile_function()
