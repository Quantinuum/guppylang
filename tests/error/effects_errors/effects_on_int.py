from collections.abc import Callable

from guppylang.decorator import guppy
from guppylang.std.effects import effects

# This says the return type (not the function) has effects
@guppy
def main(x: int) -> int @ effects():
    return x + 1

main.compile()