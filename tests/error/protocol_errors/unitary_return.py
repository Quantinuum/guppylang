from collections.abc import Callable

from guppylang import guppy
from guppylang.std.lang import Unitary
from guppylang.std.quantum import h, qubit

@guppy
def main() -> Unitary[[qubit], None]:
    return h

main.compile_function()
