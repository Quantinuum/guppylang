from guppylang import guppy
from guppylang.std.cell import Cell
from guppylang.std.lang import owned


@guppy
def main(p: Cell[int] @ owned, q: Cell[int]) -> bool:
    p.free()
    return p == q


main.compile()
