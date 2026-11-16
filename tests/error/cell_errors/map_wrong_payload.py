from guppylang import guppy
from guppylang.std.cell import Cell


@guppy
def callback(value: int, arg: int) -> tuple[bool, int]:
    return True, arg


@guppy
def main(p: Cell[int]) -> int:
    return p.map(callback, 1)


main.compile()
