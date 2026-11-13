from guppylang import guppy
from guppylang.std.cell import Cell
from guppylang.std.lang import owned


@guppy
def main(p: Cell[int]) -> bool:
    return p == 1


main.compile()
