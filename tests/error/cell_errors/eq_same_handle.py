from guppylang import guppy
from guppylang.std.cell import Cell
from guppylang.std.lang import owned


@guppy
def main(p: Cell[int]) -> bool:
    return p == p


main.compile()
