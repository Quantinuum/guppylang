from guppylang import guppy
from guppylang.std.ptr import Ptr
from guppylang.std.lang import owned


@guppy
def main(p: Ptr[int]) -> bool:
    return p == p


main.compile()
