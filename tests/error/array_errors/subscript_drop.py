from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit


@guppy.declare
def foo() -> array[qubit, 10]: ...


@guppy
def main() -> qubit:
    return foo()[0]


main.compile()