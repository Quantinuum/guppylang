"""Concrete numeric overloads and borrowed natural-order extrema."""

from functools import reduce
from operator import add, mul
from typing import Self, no_type_check

import pytest

from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.num import nat
from guppylang.std.platform import output
from guppylang_internals.error import GuppyError


@no_type_check
def test_numeric_reductions() -> None:
    integer_cases = [[], [7], [-3, 2, -1], [3, 0, 2], [2, 2, 2]]
    float_cases = [[float(value) for value in values] for values in integer_cases] + [
        [1e16, 1.0, -1e16],
        [1e16, -1e16],
        [1e-200, 1e-200, 1e200],
    ]

    @guppy
    def integers[n: nat](values: array[int, n]) -> None:
        output("sum", values.sum_numeric())
        output("product", values.product_numeric())
        if n:
            output("retained", values)
        else:
            output("length", len(values))

    @guppy
    def naturals[n: nat](inputs: array[int, n]) -> None:
        values = array(nat(inputs[i]) for i in range(n))
        output("sum", values.sum_numeric())
        output("product", values.product_numeric())
        if n:
            output("retained", values)
        else:
            output("length", len(values))

    @guppy
    def floats[n: nat](values: array[float, n]) -> None:
        output("sum", values.sum_numeric())
        output("product", values.product_numeric())
        if n:
            output("retained", values)
        else:
            output("length", len(values))

    @guppy
    def empty() -> None:
        integers(array())
        naturals(array())
        floats(array())

    @guppy.comptime
    def main() -> None:
        empty()
        for values in integer_cases[1:]:
            integers(list(values))
            naturals([abs(value) for value in values])
        for values in float_cases[1:]:
            floats(list(values))

    # Match the calls above; reduce preserves the specified left-to-right order.
    # Python's builtin sum can use compensated floating-point accumulation.
    cases = [([], int), ([], int), ([], float)]
    for values in integer_cases[1:]:
        cases.extend([(values, int), ([abs(value) for value in values], int)])
    cases.extend((values, float) for values in float_cases[1:])
    expected = []
    for values, numeric_type in cases:
        expected.extend(
            [
                ("sum", reduce(add, values, numeric_type(0))),
                ("product", reduce(mul, values, numeric_type(1))),
                ("retained", values) if values else ("length", 0),
            ]
        )
    assert main.emulator(0).coinflip_sim().run()[0].entries == expected


@no_type_check
def test_numeric_extrema() -> None:
    cases = [[7], [3, -2, 1], [2, 2, 2]]

    @guppy
    def check[n: nat](values: array[int, n]) -> None:
        output("min", values.min())
        output("max", values.max())
        output("retained", values)

    @guppy
    def other_types() -> None:
        ns = array(nat(3), nat(1))
        fs = array(1.5, -2.5)
        output("nat_min", ns.min())
        output("nat_max", ns.max())
        output("float_min", fs.min())
        output("float_max", fs.max())

    @guppy.comptime
    def main() -> None:
        for values in cases:
            check(list(values))
        other_types()

    expected = []
    for values in cases:
        expected.extend(
            [("min", min(values)), ("max", max(values)), ("retained", values)]
        )
    expected.extend(
        [("nat_min", 1), ("nat_max", 3), ("float_min", -2.5), ("float_max", 1.5)]
    )
    assert main.emulator(0).coinflip_sim().run()[0].entries == expected


@no_type_check
def test_custom_ordering_and_ties() -> None:
    @guppy.struct(frozen=True)
    class Record:
        key: int
        label: int

        @guppy
        def __lt__(self: Self, other: Self) -> bool:
            output("compare", self.label)
            # Order by magnitude; opposite signs can tie.
            return self.key * self.key < other.key * other.key

    @guppy
    def main() -> None:
        values = array(Record(-2, 10), Record(1, 20), Record(-1, 30), Record(2, 40))
        output("min_label", values.min().label)
        output("max_label", values.max().label)
        output("retained", values[0].label)

    assert main.emulator(0).coinflip_sim().run()[0].entries == [
        ("compare", 20),
        ("compare", 30),
        ("compare", 40),
        ("min_label", 20),
        ("compare", 10),
        ("compare", 10),
        ("compare", 10),
        ("max_label", 10),
        ("retained", 10),
    ]


@pytest.mark.parametrize("operation", ["min", "max"])
@no_type_check
def test_extrema_reject_empty(operation: str) -> None:
    extreme = getattr(array, operation)

    @guppy
    def main(values: array[int, 0]) -> int:
        return extreme(values)

    with pytest.raises(
        GuppyError, match=rf"array\.{operation}\(\) requires a non-empty array"
    ):
        main.compile_function()
