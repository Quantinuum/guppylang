"""Print invalid-shape compiler diagnostics for manual inspection.

Run from the repository root:
    .venv/bin/python examples/invalid_array_shapes.py

Every example should fail compilation. Inspect whether the diagnostic points
to the invalid call in this file or to the implementation in std/array.py.
"""

# ruff: noqa: T201 - This script displays compiler diagnostics.

from typing import no_type_check

from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.lang import owned
from guppylang_internals.error import GuppyError


@guppy
@no_type_check
def invalid_split(xs: array[int, 2] @ owned) -> None:
    xs.split_at(3)


@guppy
@no_type_check
def zero_chunk_size(xs: array[int, 4] @ owned) -> None:
    xs.chunks(0)


@guppy
@no_type_check
def non_dividing_chunk_size(xs: array[int, 4] @ owned) -> None:
    xs.chunks(3)


@guppy
@no_type_check
def oversized_subarray(xs: array[int, 2]) -> None:
    xs.subarray(0, 3)


def main() -> int:
    cases = [
        ("split_at(3) on an array of length 2", invalid_split),
        ("chunks(0) on an array of length 4", zero_chunk_size),
        ("chunks(3) on an array of length 4", non_dividing_chunk_size),
        ("subarray(0, 3) on an array of length 2", oversized_subarray),
    ]
    unexpected_success = False
    for description, function in cases:
        print(f"\n=== {description} ===", flush=True)
        try:
            function.compile_function()
        except GuppyError as error:
            print(error)
        else:
            print("UNEXPECTED: compilation succeeded.")
            unexpected_success = True
    return int(unexpected_success)


if __name__ == "__main__":
    raise SystemExit(main())
