from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit
from guppylang.decorator import guppy

T = guppy.type_var("T", copyable=False, droppable=True)


@guppy
def foo(x: T @ owned) -> T:
    return x


@guppy
def main() -> None:
    f = foo[qubit]


main.compile()
