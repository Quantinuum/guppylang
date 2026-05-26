from collections.abc import Callable

from guppylang.decorator import guppy

@guppy(effects=[])
def main(impure_f: Callable[[int], int, [ANY]]) -> int:
   return impure_f(5)

main.compile()
