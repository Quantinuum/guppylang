from guppylang import guppy
from guppylang.std.ptr import Ptr
from guppylang.std.lang import owned


@guppy
def main(p: Ptr[int] @ owned, q: Ptr[int] @ owned) -> bool:
    return p == q


main.compile()
