from guppylang import qubit
from guppylang.decorator import guppy
from guppylang.std.lang import owned


@guppy
def foo[T](x: T @ owned) -> tuple[T, T]:
    # T is not copyable
    return x, x


@guppy
def main() -> tuple[int, int]:
    # This fails the parametric check, even though the monomorphisation would be ok:
    return foo(0)


main.compile()
