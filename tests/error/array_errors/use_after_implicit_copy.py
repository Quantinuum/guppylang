from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned


@guppy
def main(xs: array[int, 2] @ owned) -> array[int, 2]:
   ys = xs
   return xs

main.compile_function()
