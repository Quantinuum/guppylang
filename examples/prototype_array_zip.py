"""Throwaway prototype: truncating zip with explicit ownership rules.

Run: .venv/bin/python examples/prototype_array_zip.py

zip_shortest models strict=False for droppable elements. Unmatched suffixes
are dropped when the function returns. zip_with_remainders supports linear
elements by returning both suffixes to the caller instead.
"""

# ruff: noqa: T201 - This prototype prints its state for inspection.

from __future__ import annotations

from typing import no_type_check

from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.lang import Drop, comptime, owned
from guppylang.std.num import nat
from guppylang.std.platform import output
from guppylang.std.quantum import measure, qubit, x


@guppy
@no_type_check
def zip_shortest[T: Drop, U: Drop, n: nat, m: nat](
    xs: array[T, n] @ owned, ys: array[U, m] @ owned
) -> array[tuple[T, U], comptime(min(n, m))]:
    left, _unused_left = xs.split_at(comptime(min(n, m)))
    right, _unused_right = ys.split_at(comptime(min(n, m)))
    # Both unused suffixes are implicitly dropped: T and U require Drop.
    return left.zip(right)


@guppy
@no_type_check
def zip_with_remainders[T, U, n: nat, m: nat](
    xs: array[T, n] @ owned, ys: array[U, m] @ owned
) -> tuple[
    array[tuple[T, U], comptime(min(n, m))],
    array[T, comptime(n - min(n, m))],
    array[U, comptime(m - min(n, m))],
]:
    left, remaining_left = xs.split_at(comptime(min(n, m)))
    right, remaining_right = ys.split_at(comptime(min(n, m)))
    return left.zip(right), remaining_left, remaining_right


@guppy
@no_type_check
def demo() -> None:
    for pair in zip_shortest(array(10, 20, 30), array(True, False)):
        number, flag = pair
        output("left_longer_number", number)
        output("left_longer_flag", flag)

    for pair in zip_shortest(array(40), array(False, True)):
        number, flag = pair
        output("right_longer_number", number)
        output("right_longer_flag", flag)

    empty: array[int, 0] = array()
    output("empty_length", len(zip_shortest(empty, array(True))))

    # The Drop bound permits affine values too; Copy is unnecessary.
    rows = array(array(1), array(2))
    for pair in zip_shortest(rows, array(True)):
        row, flag = pair
        output("affine_row", row)
        output("affine_flag", flag)

    # Linear values remain the caller's responsibility, including the tail.
    qs = array(qubit() for _ in range(3))
    x(qs[1])
    pairs, remaining_qubits, remaining_flags = zip_with_remainders(
        qs, array(False, True)
    )
    for pair in pairs:
        q, flag = pair
        output("paired_qubit", measure(q).read())
        output("paired_flag", flag)
    for q in remaining_qubits:
        output("remaining_qubit", measure(q).read())
    output("remaining_flags_length", len(remaining_flags))


if __name__ == "__main__":
    print("Truncating zip: [10, 20, 30] + [True, False]; [30] is dropped.")
    print("Truncating zip: [40] + [False, True]; [True] is dropped.")
    print("Affine input: [[1], [2]] + [True]; [[2]] is dropped.")
    print("Linear input: 3 qubits + 2 flags; the unmatched qubit is returned.")
    for tag, value in demo.emulator(3).stabilizer_sim().run()[0].entries:
        print(f"{tag}: {value}")
