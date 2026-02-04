from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit


@guppy
def main(qs: array[qubit, 42]) -> tuple[qubit, array[qubit, 42]]:
    q = qs[0]
    return q, qs


main.compile_function()