from guppylang.decorator import guppy, Effect

@guppy.declare(effects=[Effect.ANY])
def impure_func(x: int) -> int: ...

@guppy(effects=[])
def main() -> int:
   return impure_func(5)

main.compile()
