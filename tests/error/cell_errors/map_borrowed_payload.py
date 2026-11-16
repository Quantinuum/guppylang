from guppylang import guppy
from guppylang.std.cell import Cell
from guppylang.std.quantum import qubit


@guppy
def callback(q: qubit, arg: int) -> tuple[qubit, int]:
    return qubit(), arg


@guppy
def main(p: Cell[qubit]) -> int:
    return p.map(callback, 1)


main.compile()
