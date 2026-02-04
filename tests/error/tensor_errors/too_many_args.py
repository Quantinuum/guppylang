from guppylang.decorator import guppy

@guppy.declare
def foo(x: int) -> int:
    ...

@guppy
def main() -> int:
    return (foo, foo)(1, 2, 3)

main.compile()
