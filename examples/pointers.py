"""Share a mutable cell and explicitly recover its payload."""

from guppylang import guppy
from guppylang.std.ptr import Ptr


@guppy
def increment(value: int, amount: int) -> tuple[int, int]:
    return value + amount, value


@guppy
def main() -> tuple[int, bool, bool]:
    cell = Ptr(40)
    previous = cell.map(increment, 2)
    alias = cell.copy()
    same_cell = cell == alias  # Copying a handle preserves cell identity.
    separate = Ptr(42)
    different_cell = cell != separate  # Equal payloads can live in different cells.
    separate.free()
    alias.free().unwrap_nothing()
    return cell.free().unwrap() - previous, same_cell, different_cell


if __name__ == "__main__":
    main.compile()
