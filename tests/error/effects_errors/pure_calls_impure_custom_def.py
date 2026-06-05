from guppylang.decorator import guppy

def custom_pure(func):
    return guppy(effects=[])(func)

@guppy
def impure_func(x: int) -> int:
    return x + 1

@custom_pure
def main() -> int:
   return impure_func(5)

main.compile()