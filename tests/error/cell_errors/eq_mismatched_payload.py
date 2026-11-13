from guppylang import guppy
from guppylang.std.cell import Cell
from guppylang.std.lang import owned


@guppy
def main(p: Cell[int], q: Cell[bool]) -> bool:
    return p == q


main.compile()
