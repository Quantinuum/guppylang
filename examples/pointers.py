"""Share a mutable cell and explicitly recover its payload."""

from guppylang import guppy
from guppylang.std.ptr import Ptr


@guppy
def increment(value: int, amount: int) -> tuple[int, int]:
    return value + amount, value


@guppy
def main() -> int:
    cell = Ptr(40)
    previous = cell.map(increment, 2)
    alias = cell.copy()
    alias.free().unwrap_nothing()
    return cell.free().unwrap() - previous


if __name__ == "__main__":
    main.compile()
