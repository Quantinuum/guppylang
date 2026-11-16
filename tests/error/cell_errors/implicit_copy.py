from guppylang import guppy
from guppylang.std.cell import Cell
from guppylang.std.quantum import qubit
from guppylang.std.lang import owned


@guppy
def main(p: Cell[int] @ owned) -> tuple[Cell[int], Cell[int]]:
    return p, p

main.compile()
