from guppylang import guppy
from guppylang.std.ptr import Ptr
from guppylang.std.quantum import qubit


@guppy
def callback(q: qubit, arg: int) -> tuple[qubit, int]:
    return qubit(), arg


@guppy
def main(p: Ptr[qubit]) -> int:
    return p.map(callback, 1)


main.compile()
