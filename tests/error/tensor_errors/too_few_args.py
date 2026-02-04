from guppylang.decorator import guppy

@guppy.declare
def foo(x: int) -> int:
    ...

@guppy
def main() -> int:
    return (foo, foo)(42)

main.compile()
