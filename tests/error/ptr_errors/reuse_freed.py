from guppylang import guppy
from guppylang.std.ptr import Ptr
from guppylang.std.quantum import qubit
from guppylang.std.lang import owned


@guppy
def main() -> int:
    p = Ptr(1)
    p.free()
    return p.read()

main.compile()
