from guppylang import guppy
from guppylang.std.array import array


@guppy
def array_out_of_bounds_other_file(x: int) -> int:
    arr = array(1, 2, 3)
    return arr[x]
