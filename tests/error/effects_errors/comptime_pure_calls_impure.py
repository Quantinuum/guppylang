from guppylang.decorator import guppy

@guppy.comptime
def impure_func(x: int) -> int:
    return x + 1

@guppy.comptime(effects=[])
def main() -> int:
    return impure_func(5)

main.compile()
