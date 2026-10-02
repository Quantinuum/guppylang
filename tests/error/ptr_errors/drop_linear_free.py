from guppylang import guppy
from guppylang.std.ptr import Ptr
from guppylang.std.quantum import qubit
from guppylang.std.lang import owned


@guppy
def main(q: qubit @ owned) -> None:
    Ptr(q).free()

main.compile()
