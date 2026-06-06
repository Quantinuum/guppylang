from guppylang.decorator import guppy

@guppy
def impure_func(x: int) -> int:
    return x + 1

@guppy.comptime(effects=None)
def main() -> int:
    return impure_func(5)

main.compile()
