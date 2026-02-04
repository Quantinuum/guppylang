from guppylang.decorator import guppy

T = guppy.type_var("T")

@guppy.declare
def foo(x: T) -> T:
    ...

@guppy
def main() -> int:
    return (foo, foo)(42, 42)

main.compile()
