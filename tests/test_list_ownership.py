import pytest
from guppylang import guppy, qubit
from guppylang.std.lang import owned
from guppylang_internals.error import GuppyError
from guppylang_internals.tys.builtin import int_type, list_type
from guppylang_internals.tys.param import TypeParam


@pytest.fixture(autouse=True)
def enable_lists(use_experimental_features):
    pass


def test_list_bounds():
    ints = list_type(int_type())
    linear = TypeParam(0, "T", must_be_copyable=False, must_be_droppable=False)
    qubits = list_type(linear.to_bound(0).ty)
    nested = list_type(ints)
    assert not ints.copyable
    assert ints.droppable
    assert not qubits.copyable
    assert not qubits.droppable
    assert not nested.copyable
    assert nested.droppable


def test_duplicate_list_rejected():
    @guppy
    def duplicate(xs: list[int] @ owned) -> tuple[list[int], list[int]]:
        return xs, xs

    with pytest.raises(GuppyError, match="Copy violation"):
        duplicate.check()


def test_use_after_move_rejected():
    @guppy
    def moved(xs: list[int] @ owned) -> tuple[list[int], int]:
        ys = xs
        return ys, len(xs)

    with pytest.raises(GuppyError, match="Copy violation"):
        moved.check()


def test_nested_list_copy_rejected():
    @guppy
    def duplicate(
        xs: tuple[list[int], int] @ owned,
    ) -> tuple[tuple[list[int], int], tuple[list[int], int]]:
        ys = xs
        return xs, ys

    with pytest.raises(GuppyError):
        duplicate.check()


def test_nondroppable_elements_rejected():
    @guppy
    def discard(xs: list[qubit] @ owned) -> None:
        pass

    with pytest.raises(GuppyError, match="Drop violation"):
        discard.check()


def test_borrow_and_move():
    @guppy
    def borrow(xs: list[int]) -> int:
        xs.append(2)
        return xs[0] + len(xs)

    @guppy
    def move(xs: list[int] @ owned) -> list[int]:
        borrow(xs)
        return xs

    move.check()


def test_iteration_requires_ownership():
    @guppy
    def iterate(xs: list[int]) -> int:
        total = 0
        for x in xs:
            total += x
        return total

    with pytest.raises(GuppyError, match=r"borrowed|Not owned"):
        iterate.check()


def test_repeated_iteration_rejected():
    @guppy
    def iterate(xs: list[int] @ owned) -> int:
        total = 0
        for x in xs:
            total += x
        for x in xs:
            total += x
        return total

    with pytest.raises(GuppyError, match="Copy violation"):
        iterate.check()


def test_linear_indexed_read_rejected():
    @guppy
    def access(xs: list[qubit]) -> qubit:
        return xs.__getitem__(0)

    with pytest.raises(GuppyError, match="copyable"):
        access.check()


def test_nondroppable_setitem_rejected():
    @guppy
    def replace(xs: list[qubit], q: qubit @ owned) -> None:
        xs.__setitem__(0, q)

    with pytest.raises(GuppyError, match="droppable"):
        replace.check()


def test_swap_returned_linear_element_must_be_consumed():
    @guppy
    def replace(xs: list[qubit], q: qubit @ owned) -> None:
        xs.swap(0, q)

    with pytest.raises(GuppyError, match="Drop violation"):
        replace.check()
