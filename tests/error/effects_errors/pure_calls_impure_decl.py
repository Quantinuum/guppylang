from guppylang.decorator import guppy

@guppy.declare
def impure_func(x: int) -> int: ...

@guppy(max_effects=[])
def main() -> int:
   return impure_func(5)

main.compile()