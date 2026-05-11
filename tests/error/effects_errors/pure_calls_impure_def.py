from guppylang.decorator import guppy

@guppy
def impure_func(x: int) -> int:
    return x + 1

@guppy(max_effects=[])
def main() -> int:
   return impure_func(5)

main.compile()