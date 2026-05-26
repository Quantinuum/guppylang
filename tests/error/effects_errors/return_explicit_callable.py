from guppylang.decorator import guppy, Effect

@guppy(effects=[Effect.ANY])
def impure_func(x: int) -> int:
    return x + 1

@guppy
def main() -> Callable[[int], int, []]:
   return impure_func

main.compile()
