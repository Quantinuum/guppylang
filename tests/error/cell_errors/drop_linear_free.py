from guppylang import guppy
from guppylang.std.cell import Cell
from guppylang.std.quantum import qubit
from guppylang.std.lang import owned


@guppy
def main(q: qubit @ owned) -> None:
    Cell(q).free()

main.compile()
