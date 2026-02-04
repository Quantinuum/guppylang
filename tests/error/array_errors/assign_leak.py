from guppylang.decorator import guppy
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit


@guppy
def main() -> None:
    qs = array(qubit() for _ in range(10)) 
    qs[0] = qubit()  # Leaks the old qubit at index 0


main.compile()