from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy.declare
def foo() -> array[int, 10]: ...

@guppy
def main() -> None:
    foo()[0] = 22

main.compile()