from collections.abc import Callable

from guppylang.decorator import guppy, Effect
from guppylang.std.effects import effects

@guppy(effects=[Effect.ANY])
def impure_func(x: int) -> int:
    return x + 1

@guppy
def main() -> Callable[[int], int] @effects():
   return impure_func

main.compile()
