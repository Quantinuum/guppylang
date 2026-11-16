from guppylang import guppy
from guppylang.std.cell import Cell
from guppylang.std.quantum import qubit
from guppylang.std.lang import owned


@guppy
def main() -> int:
    p = Cell(1)
    p.free()
    return p.read()

main.compile()
