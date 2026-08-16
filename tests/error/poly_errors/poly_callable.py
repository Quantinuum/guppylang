from collections.abc import Callable

from guppylang.decorator import guppy

T = guppy.type_var("T")


@guppy.declare
def foo(x: T) -> T:
    ...

@guppy
def main() -> int:
    ff = foo
    i: int = ff(3)
    # Type inference could allow inferring a type argument above,
    # but does not ATM; if we extend inference to do so then the below
    # extends the test to make inference impossible:
    #f: float = ff(3.14)
    return i


main.compile()
