from guppylang import guppy
from guppylang.std.ptr import Ptr
from guppylang.std.quantum import qubit
from guppylang.std.lang import owned


@guppy
def main(p: Ptr[qubit], q: qubit @ owned) -> None:
    p.write(q)

main.compile()
