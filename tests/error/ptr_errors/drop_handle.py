from guppylang import guppy
from guppylang.std.ptr import Ptr
from guppylang.std.quantum import qubit
from guppylang.std.lang import owned


@guppy
def main() -> None:
    p = Ptr(1)

main.compile()
