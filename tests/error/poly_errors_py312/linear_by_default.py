from guppylang import qubit
from guppylang.decorator import guppy
from guppylang.std.lang import owned


@guppy
def foo[T](x: T @ owned) -> tuple[T, T]:
    # T is not copyable
    return x, x


@guppy
def main() -> tuple[qubit, qubit]:
    return foo(qubit())


main.compile()
