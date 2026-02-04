from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned
from guppylang.std.quantum import qubit


@guppy.declare
def foo(q: qubit, qs: array[qubit, 42] @owned) -> array[qubit, 42]: ...


@guppy
def main(qs: array[qubit, 42] @owned) -> array[qubit, 42]:
    return foo(qs[0], qs)


main.compile_function()
