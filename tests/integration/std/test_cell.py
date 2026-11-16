from itertools import pairwise

import pytest
from hugr.cli import validate as validate_hugr
from hugr.envelope import EnvelopeConfig, EnvelopeFormat

from guppylang import guppy
from guppylang.std.lang import Function, owned
from guppylang.std.cell import Cell
from guppylang.std.quantum import qubit, discard, measure, x


@pytest.fixture
def validate_cell():
    # Both serialized forms must use the matching pointer extension. Runtime
    # tests additionally exercise the ordinary emulator with a compatible QIS
    # compiler, selected explicitly by the test environment.
    def validate(package):
        validate_hugr(package.to_bytes())
        validate_hugr(package.to_bytes(EnvelopeConfig(format=EnvelopeFormat.JSON)))

    return validate


def test_copyable(validate_cell, run_int_fn):
    @guppy
    def main() -> int:
        p = Cell(1)
        p.write(2)
        old = p.swap(3)
        other = p.copy()
        other.free().unwrap_nothing()
        return old + p.read() + p.free().unwrap()

    validate_cell(main.compile_function())

    run_int_fn(main, 8)


def test_linear(validate_cell, run_int_fn):
    @guppy
    def main(q: qubit @ owned, replacement: qubit @ owned) -> qubit:
        p = Cell(q)
        discard(p.swap(replacement))
        other = p.copy()
        other.free().unwrap_nothing()
        return p.free().unwrap()

    validate_cell(main.compile_function())

    @guppy
    def entry() -> int:
        original, replacement = qubit(), qubit()
        x(replacement)
        return int(bool(measure(main(original, replacement))))

    run_int_fn(entry, 1, num_qubits=2)


def test_map(validate_cell, run_int_fn):
    @guppy
    def transform(q: qubit @ owned, replacement: qubit @ owned) -> tuple[qubit, qubit]:
        return replacement, q

    @guppy
    def main(q: qubit @ owned, replacement: qubit @ owned) -> tuple[qubit, qubit]:
        p = Cell(q)
        old = p.map(transform, replacement)
        return old, p.free().unwrap()

    validate_cell(main.compile_function())

    @guppy
    def entry() -> int:
        original, replacement = qubit(), qubit()
        x(original)
        old, new = main(original, replacement)
        return 2 * int(bool(measure(old))) + int(bool(measure(new)))

    run_int_fn(entry, 2, num_qubits=2)


def test_tuple_and_unit(validate_cell, run_int_fn):
    @guppy
    def transform(value: tuple[int, bool], arg: None) -> tuple[tuple[int, bool], None]:
        return value, arg

    @guppy
    def main() -> tuple[int, bool]:
        p = Cell((1, True))
        p.map(transform, None)
        p.read()
        p.swap((2, False))
        p.write((3, True))
        unit = Cell(None)
        unit.read()
        unit.swap(None)
        unit.free().unwrap()
        return p.free().unwrap()

    validate_cell(main.compile_function())

    @guppy
    def entry() -> int:
        value, flag = main()
        return value + int(flag)

    run_int_fn(entry, 4)


def test_borrowed_and_higher_order(validate_cell, run_int_fn):
    @guppy
    def change(p: Cell[int]) -> int:
        f: Function[[Cell[int], int], int] = Cell.swap
        return f(p, 42)

    @guppy
    def main() -> int:
        p = Cell(1)
        change(p)
        return p.free().unwrap()

    validate_cell(main.compile_function())

    run_int_fn(main, 42)


def test_nested_payload(validate_cell, run_int_fn):
    @guppy
    def main() -> int:
        outer = Cell(Cell(42))
        inner = outer.free().unwrap()
        return inner.free().unwrap()

    validate_cell(main.compile_function())

    run_int_fn(main, 42)


def test_map_tuple_result(validate_cell, run_int_fn):
    @guppy
    def transform(value: int, arg: tuple[int, bool]) -> tuple[int, tuple[int, bool]]:
        amount, flag = arg
        return value + amount, (value, flag)

    @guppy
    def main() -> tuple[int, bool]:
        p = Cell(40)
        result = p.map(transform, (2, True))
        p.free()
        return result

    validate_cell(main.compile_function())

    @guppy
    def entry() -> int:
        value, flag = main()
        return value + int(flag)

    run_int_fn(entry, 41)


def test_handle_sequencing(validate_cell, run_int_fn):
    from tests.integration.test_side_effect_ordering import find_ext_nodes

    @guppy
    def main() -> int:
        p = Cell(1)
        p.write(2)
        p.swap(3)
        result = p.read()
        p.free()
        return result

    package = main.compile_function()
    validate_cell(package)
    graph = package.modules[0]
    nodes = [
        find_ext_nodes(graph, "ptr." + name)[0]
        for name in ["New", "Write", "Swap", "Read", "Free"]
    ]
    for before, after in pairwise(nodes):
        assert after.inp(0) in graph.linked_ports(before.out(0))

    run_int_fn(main, 3)


def test_identity_equality(validate_cell, run_int_fn):
    from tests.integration.test_side_effect_ordering import find_ext_nodes

    @guppy
    def main() -> tuple[bool, bool]:
        p = Cell(42)
        alias = p.copy()
        separate = Cell(42)
        same = p == alias
        different = p == separate
        alias.free()
        p.free()
        separate.free()
        return same, different

    package = main.compile_function()
    validate_cell(package)
    graph = package.modules[0]
    first, second = find_ext_nodes(graph, "ptr.Eq")
    # Equality threads each borrowed handle in its original input order.
    assert second.inp(0) in graph.linked_ports(first.out(0))
    frees = find_ext_nodes(graph, "ptr.Free")
    assert frees[0].inp(0) in graph.linked_ports(first.out(1))
    assert frees[1].inp(0) in graph.linked_ports(second.out(0))
    assert frees[2].inp(0) in graph.linked_ports(second.out(1))

    @guppy
    def entry() -> int:
        same, different = main()
        return int(same) + 2 * int(different)

    run_int_fn(entry, 1)


def test_equality_linear_and_higher_order(validate_cell, run_int_fn):
    @guppy
    def compare(p: Cell[qubit], q: Cell[qubit]) -> bool:
        f: Function[[Cell[qubit], Cell[qubit]], bool] = Cell.__eq__
        return f(p, q)

    @guppy
    def main(q: qubit @ owned) -> tuple[bool, bool, qubit]:
        p = Cell(q)
        alias = p.copy()
        same = compare(p, alias)
        different = p != alias
        alias.free().unwrap_nothing()
        return same, different, p.free().unwrap()

    validate_cell(main.compile_function())

    @guppy
    def entry() -> int:
        q = qubit()
        x(q)
        same, different, returned = main(q)
        return int(same) + 2 * int(different) + 4 * int(bool(measure(returned)))

    run_int_fn(entry, 5, num_qubits=1)


def test_equality_tuple_unit_and_inequality(validate_cell, run_int_fn):
    @guppy
    def main() -> tuple[bool, bool]:
        p = Cell((1, True))
        q = p.copy()
        different = p != q
        p.free()
        q.free()
        unit = Cell(None)
        other = unit.copy()
        same = unit == other
        unit.free()
        other.free()
        return different, same

    validate_cell(main.compile_function())

    @guppy
    def entry() -> int:
        different, same = main()
        return int(different) + 2 * int(same)

    run_int_fn(entry, 2)


def test_map_restores_payload_and_availability(run_int_fn):
    @guppy
    def add(value: int, amount: int) -> tuple[int, int]:
        return value + amount, value

    @guppy
    def main() -> int:
        p = Cell(40)
        first = p.map(add, 2)
        second = p.map(add, 3)
        return first + second + p.read() + p.free().unwrap()

    run_int_fn(main, 172)


def test_map_allows_identity_comparison(run_int_fn):
    @guppy
    def compare(
        value: int, handles: tuple[Cell[int], Cell[int]] @ owned
    ) -> tuple[int, tuple[bool, Cell[int], Cell[int]]]:
        left, right = handles
        return value, (left == right, left, right)

    @guppy
    def main() -> int:
        p = Cell(42)
        left_alias, right_alias = p.copy(), p.copy()
        same, left, right = p.map(compare, (left_alias, right_alias))
        left.free().unwrap_nothing()
        right.free().unwrap_nothing()
        return int(same) + p.free().unwrap()

    run_int_fn(main, 43)


def test_map_rejects_same_cell_payload_reentry(run_int_fn):
    from guppylang.emulator.exceptions import EmulatorError
    from selene_sim.exceptions import SelenePanicError

    @guppy
    def reenter(value: int, alias: Cell[int] @ owned) -> tuple[int, Cell[int]]:
        return value + alias.read(), alias

    @guppy
    def main() -> int:
        p = Cell(1)
        copied = p.copy()
        alias = p.map(reenter, copied)
        alias.free().unwrap_nothing()
        return p.free().unwrap()

    with pytest.raises(EmulatorError, match="Pointer cell is already locked") as error:
        run_int_fn(main, 0)
    assert isinstance(error.value.underlying_exception, SelenePanicError)
    assert error.value.underlying_exception.code == 1002
