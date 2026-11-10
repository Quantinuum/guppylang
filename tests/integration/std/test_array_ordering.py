"""Natural-order queries and heapsort, including borrowed linear records."""

from bisect import bisect_left, bisect_right
from itertools import pairwise, product
from typing import Self, no_type_check

from guppylang import guppy
from guppylang.std.array import array
from guppylang.std.num import nat
from guppylang.std.platform import output
from guppylang.std.quantum import measure, qubit, x


@no_type_check
def test_array_sorting_and_search() -> None:
    # Exhaust all short arrays over three values, then exercise deeper heaps.
    cases = [values for size in range(5) for values in product([-1, 0, 1], repeat=size)]
    cases.extend([(8, 2, 5, 1, 7, 3, 6, 4), (7, 6, 5, 4, 3, 2, 1)])
    queries = [-2, -1, 0, 1, 2]

    @guppy
    def check[n: nat](values: array[int, n]) -> None:
        output("before", values.is_sorted())
        values.sort_unstable()
        output("after", values.is_sorted())
        if n:
            output("values", values)
        for query in queries:
            found = values.binary_search(query)
            output("found", found.is_ok())
            if found.is_ok():
                output("index", found.unwrap())
            else:
                output("index", found.unwrap_err())
        if n:
            output("retained", values)

    @guppy
    def empty() -> None:
        check(array())

    @guppy
    def other_types() -> None:
        ns = array(nat(3), nat(1))
        fs = array(2.5, -1.5)
        output("nat_before", ns.is_sorted())
        output("float_before", fs.is_sorted())
        ns.sort_unstable()
        fs.sort_unstable()
        output("naturals", ns)
        output("floats", fs)
        output("nat_after", ns.is_sorted())
        output("float_after", fs.is_sorted())
        output("nat_index", ns.binary_search(nat(3)).unwrap())
        output("float_index", fs.binary_search(0.0).unwrap_err())

    @guppy.comptime
    def main() -> None:
        empty()
        for values in cases[1:]:
            check(list(values))
        other_types()

    entries = iter(main.emulator(0).coinflip_sim().run()[0].entries)
    for values in cases:
        ordered = sorted(values)
        before = all(a <= b for a, b in pairwise(values))
        assert next(entries) == ("before", before), values
        assert next(entries) == ("after", True), values
        if values:
            assert next(entries) == ("values", ordered), values
        for query in queries:
            present = query in ordered
            assert next(entries) == ("found", present), (values, query)
            tag, index = next(entries)
            assert tag == "index"
            if present:
                # Duplicates may match anywhere within their equal range.
                assert (
                    bisect_left(ordered, query) <= index < bisect_right(ordered, query)
                )
            else:
                assert index == bisect_left(ordered, query), (values, query)
        if values:
            assert next(entries) == ("retained", ordered), values
    assert list(entries) == [
        ("nat_before", False),
        ("float_before", False),
        ("naturals", [1, 3]),
        ("floats", [-1.5, 2.5]),
        ("nat_after", True),
        ("float_after", True),
        ("nat_index", 1),
        ("float_index", 1),
    ]


@no_type_check
def test_linear_record_ordering() -> None:
    @guppy.struct
    class Record:
        key: int
        q: qubit

        @guppy
        def __lt__(self: Self, other: Self) -> bool:
            # This type orders keys in descending numeric order.
            return self.key > other.key

    @guppy
    def main() -> None:
        values = array(
            Record(2, qubit()),
            Record(4, qubit()),
            Record(1, qubit()),
            Record(3, qubit()),
        )
        x(values[1].q)
        x(values[2].q)
        output("before", values.is_sorted())
        values.sort_unstable()
        output("after", values.is_sorted())
        query = Record(3, qubit())
        x(query.q)
        output("index", values.binary_search(query).unwrap())
        # Reuse the borrowed query and each sorted record before consuming qubits.
        output("query", query.key)
        output("query_qubit", measure(query.q).read())
        for record in values:
            output("key", record.key)
            output("qubit", measure(record.q).read())

    assert main.emulator(5).stabilizer_sim().run()[0].entries == [
        ("before", False),
        ("after", True),
        ("index", 1),
        ("query", 3),
        ("query_qubit", True),
        ("key", 4),
        ("qubit", True),
        ("key", 3),
        ("qubit", False),
        ("key", 2),
        ("qubit", False),
        ("key", 1),
        ("qubit", True),
    ]
