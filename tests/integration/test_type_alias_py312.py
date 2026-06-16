"""Tests for Python 3.12+ `type` statement syntax with guppy.type_alias."""

from typing import Generic

from guppylang import guppy
from guppylang.std.lang import Copy, Drop


def test_simple_alias_from_type_stmt(run_int_fn):
    """A plain `type X = "..."` alias works just like the string form."""
    type MyInt = "int"
    MyInt = guppy.type_alias(MyInt)

    @guppy
    def main(x: MyInt) -> MyInt:
        return x + 1

    run_int_fn(main, expected=42, args=[41])


def test_generic_alias_from_type_stmt(run_int_fn):
    """Generic type params on the `type` statement become guppy TypeParams.

    `T: (Copy, Drop)` in the ``type`` statement corresponds to the default
    ``guppy.type_var("T")`` (copyable=True, droppable=True).
    """
    T = guppy.type_var("T")  # copyable=True, droppable=True by default

    @guppy.struct
    class Box(Generic[T]):
        value: T

    # T: (Copy, Drop) matches the default guppy.type_var("T") constraints
    type Boxed[T: (Copy, Drop)] = "Box[T]"
    Boxed = guppy.type_alias(Boxed)

    @guppy
    def unwrap(b: Boxed[int]) -> int:
        return b.value

    @guppy
    def main() -> int:
        return unwrap(Box(99))

    run_int_fn(main, expected=99)


def test_two_param_alias_from_type_stmt(run_int_fn):
    """Two type parameters are registered in declaration order."""
    A = guppy.type_var("A")  # copyable=True, droppable=True by default
    B = guppy.type_var("B")

    @guppy.struct
    class Pair(Generic[A, B]):
        first: A
        second: B

    # A: (Copy, Drop), B: (Copy, Drop) to match the struct's constraints
    type SwappedPair[A: (Copy, Drop), B: (Copy, Drop)] = "Pair[B, A]"
    SwappedPair = guppy.type_alias(SwappedPair)

    @guppy
    def main() -> int:
        # SwappedPair[int, bool] → Pair[bool, int], so .second is int
        sp: SwappedPair[int, bool] = Pair(True, 42)
        return sp.second

    run_int_fn(main, expected=42)


def test_copy_bound_from_type_stmt(validate):
    """`T: Copy` bound is correctly translated to a copyable TypeParam."""
    # Use copyable=True, droppable=False so the struct matches T: Copy
    T = guppy.type_var("T", copyable=True, droppable=False)

    @guppy.struct
    class Container(Generic[T]):
        item: T

    # T: Copy → must_be_copyable=True, must_be_droppable=False
    type CopyAlias[T: Copy] = "Container[T]"
    CopyAlias = guppy.type_alias(CopyAlias)

    @guppy
    def duplicate(c: CopyAlias[int]) -> tuple[int, int]:
        return c.item, c.item

    validate(duplicate.compile_function())


def test_chain_via_type_stmt(run_int_fn):
    """A `type` statement alias that chains through another alias resolves correctly."""
    type Base = "int"
    Base = guppy.type_alias(Base)

    type Derived = "Base"
    Derived = guppy.type_alias(Derived)

    @guppy
    def main(x: Derived) -> Base:
        return x * 2

    run_int_fn(main, expected=10, args=[5])
