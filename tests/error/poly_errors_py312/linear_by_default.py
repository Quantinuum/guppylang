from guppylang.decorator import guppy
from guppylang.std.lang import owned


@guppy
def main[T](x: T @ owned) -> tuple[T, T]:
    # T is not copyable
    return x, x


main.compile()
