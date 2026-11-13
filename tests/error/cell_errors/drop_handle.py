from guppylang import guppy
from guppylang.std.cell import Cell
from guppylang.std.quantum import qubit
from guppylang.std.lang import owned


@guppy
def main() -> None:
    p = Cell(1)

main.compile()
