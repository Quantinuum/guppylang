from guppylang.decorator import guppy

@guppy(max_effects=[])
def pure_func(x: int) -> int:
    return x + 1

# This is an error because we enforce invariance of Callable types.
@guppy
def main() -> Callable[[int], int]:
   return pure_func

main.compile()