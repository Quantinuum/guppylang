from guppylang.decorator import guppy, Effect

@guppy.declare(max_effects=[Effect.ANY])
def impure_func(x: int) -> int: ...

@guppy(max_effects=[])
def main() -> int:
   return impure_func(5)

main.compile()
