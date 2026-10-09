from guppylang import guppy
from guppylang.std.ptr import Ptr


@guppy
def callback(value: int, arg: int) -> tuple[bool, int]:
    return True, arg


@guppy
def main(p: Ptr[int]) -> int:
    return p.map(callback, 1)


main.compile()
