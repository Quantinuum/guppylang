from itertools import pairwise

import pytest
from hugr.cli import validate as validate_hugr
from hugr.envelope import EnvelopeConfig, EnvelopeFormat

from guppylang import guppy
from guppylang.std.lang import Function, owned
from guppylang.std.ptr import Ptr
from guppylang.std.quantum import qubit, discard


@pytest.fixture
def validate_ptr():
    # The released QIS validator embeds ptr 0.1. Validate with the pinned HUGR
    # Rust implementation of ptr 0.2 until the matching QIS compiler is released.
    # Do not export these graphs for CI normalization: that stage also uses the
    # released QIS validator and tket passes, which cannot consume ptr 0.2 yet.
    def validate(package):
        payload = package.to_bytes()
        validate_hugr(payload)
        validate_hugr(package.to_bytes(EnvelopeConfig(format=EnvelopeFormat.JSON)))

    return validate


def test_copyable(validate_ptr):
    @guppy
    def main() -> int:
        p = Ptr(1)
        p.write(2)
        old = p.swap(3)
        other = p.copy()
        other.free().unwrap_nothing()
        return old + p.read() + p.free().unwrap()

    validate_ptr(main.compile_function())


def test_linear(validate_ptr):
    @guppy
    def main(q: qubit @ owned, replacement: qubit @ owned) -> qubit:
        p = Ptr(q)
        discard(p.swap(replacement))
        other = p.copy()
        other.free().unwrap_nothing()
        return p.free().unwrap()

    validate_ptr(main.compile_function())


def test_map(validate_ptr):
    @guppy
    def transform(q: qubit @ owned, replacement: qubit @ owned) -> tuple[qubit, qubit]:
        return replacement, q

    @guppy
    def main(q: qubit @ owned, replacement: qubit @ owned) -> tuple[qubit, qubit]:
        p = Ptr(q)
        old = p.map(transform, replacement)
        return old, p.free().unwrap()

    validate_ptr(main.compile_function())


def test_tuple_and_unit(validate_ptr):
    @guppy
    def transform(value: tuple[int, bool], arg: None) -> tuple[tuple[int, bool], None]:
        return value, arg

    @guppy
    def main() -> tuple[int, bool]:
        p = Ptr((1, True))
        p.map(transform, None)
        p.read()
        p.swap((2, False))
        p.write((3, True))
        unit = Ptr(None)
        unit.read()
        unit.swap(None)
        unit.free().unwrap()
        return p.free().unwrap()

    validate_ptr(main.compile_function())


def test_borrowed_and_higher_order(validate_ptr):
    @guppy
    def change(p: Ptr[int]) -> int:
        f: Function[[Ptr[int], int], int] = Ptr.swap
        return f(p, 42)

    @guppy
    def main() -> int:
        p = Ptr(1)
        change(p)
        return p.free().unwrap()

    validate_ptr(main.compile_function())


def test_nested_payload(validate_ptr):
    @guppy
    def main() -> int:
        outer = Ptr(Ptr(42))
        inner = outer.free().unwrap()
        return inner.free().unwrap()

    validate_ptr(main.compile_function())


def test_map_tuple_result(validate_ptr):
    @guppy
    def transform(value: int, arg: tuple[int, bool]) -> tuple[int, tuple[int, bool]]:
        amount, flag = arg
        return value + amount, (value, flag)

    @guppy
    def main() -> tuple[int, bool]:
        p = Ptr(40)
        result = p.map(transform, (2, True))
        p.free()
        return result

    validate_ptr(main.compile_function())


def test_handle_sequencing(validate_ptr):
    from tests.integration.test_side_effect_ordering import find_ext_nodes

    @guppy
    def main() -> int:
        p = Ptr(1)
        p.write(2)
        p.swap(3)
        result = p.read()
        p.free()
        return result

    package = main.compile_function()
    validate_ptr(package)
    graph = package.modules[0]
    nodes = [
        find_ext_nodes(graph, "ptr." + name)[0]
        for name in ["New", "Write", "Swap", "Read", "Free"]
    ]
    for before, after in pairwise(nodes):
        assert after.inp(0) in graph.linked_ports(before.out(0))


def test_identity_equality(validate_ptr):
    from tests.integration.test_side_effect_ordering import find_ext_nodes

    @guppy
    def main() -> tuple[bool, bool]:
        p = Ptr(42)
        alias = p.copy()
        separate = Ptr(42)
        same = p == alias
        different = p == separate
        alias.free()
        p.free()
        separate.free()
        return same, different

    package = main.compile_function()
    validate_ptr(package)
    graph = package.modules[0]
    first, second = find_ext_nodes(graph, "ptr.Eq")
    # Equality threads each borrowed handle in its original input order.
    assert second.inp(0) in graph.linked_ports(first.out(0))
    frees = find_ext_nodes(graph, "ptr.Free")
    assert frees[0].inp(0) in graph.linked_ports(first.out(1))
    assert frees[1].inp(0) in graph.linked_ports(second.out(0))
    assert frees[2].inp(0) in graph.linked_ports(second.out(1))


def test_equality_linear_and_higher_order(validate_ptr):
    @guppy
    def compare(p: Ptr[qubit], q: Ptr[qubit]) -> bool:
        f: Function[[Ptr[qubit], Ptr[qubit]], bool] = Ptr.__eq__
        return f(p, q)

    @guppy
    def main(q: qubit @ owned) -> tuple[bool, bool, qubit]:
        p = Ptr(q)
        alias = p.copy()
        same = compare(p, alias)
        different = p != alias
        alias.free().unwrap_nothing()
        return same, different, p.free().unwrap()

    validate_ptr(main.compile_function())


def test_equality_tuple_unit_and_inequality(validate_ptr):
    @guppy
    def main() -> tuple[bool, bool]:
        p = Ptr((1, True))
        q = p.copy()
        different = p != q
        p.free()
        q.free()
        unit = Ptr(None)
        other = unit.copy()
        same = unit == other
        unit.free()
        other.free()
        return different, same

    validate_ptr(main.compile_function())
