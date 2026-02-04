from guppylang import array
from guppylang.decorator import guppy

T = guppy.type_var("T", copyable=True, droppable=False)


@guppy
def foo(x: T) -> T:
    return x


@guppy
def main() -> None:
    f = foo[array[int, 10]]


main.compile()
