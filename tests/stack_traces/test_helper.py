from guppylang import guppy
from guppylang.std.array import array


@guppy
def array_with_three_elements(x: int) -> int:
    arr = array(1, 2, 3)
    return arr[x]
