from guppylang.decorator import guppy
from guppylang.std.builtins import array

@guppy
def impure_func(x: int) -> int:
    #Use result, or similar?
    return x + 1

@guppy(max_effects=[])
def main() -> int:
   return impure_func(5)

main.compile()