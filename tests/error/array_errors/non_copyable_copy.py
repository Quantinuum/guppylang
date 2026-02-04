from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned
from guppylang.std.quantum import qubit


@guppy
def main(xs: array[qubit, 2] @ owned) -> array[int, 2]:
   ys = xs.copy()
   return ys

main.compile_function()
