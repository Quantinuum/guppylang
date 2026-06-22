from typing import Generic

from guppylang import array, guppy, qubit
from guppylang.std.builtins import owned
from guppylang.std.quantum import discard, measure, x


def test_alias_chain(run_int_fn):
    """Type aliases can chain through other aliases for scalar types."""
    MyInt = guppy.type_alias("MyInt", "int")
    MyOtherInt = guppy.type_alias("MyOtherInt", "MyInt")

    @guppy
    def main(x: MyOtherInt) -> MyInt:
        return x + 1

    run_int_fn(main, expected=42, args=[41])


def test_array_alias(validate):
    """Type aliases can name nested concrete array types."""
    Row = guppy.type_alias("Row", "array[int, 2]")
    Matrix = guppy.type_alias("Matrix", "array[Row, 2]")

    @guppy
    def main(xs: Matrix) -> int:
        return xs[0][0] + xs[0][1] + xs[1][0] + xs[1][1]

    validate(main.compile_function())


def test_qubit_array_alias(run_int_fn):
    """Type aliases preserve owned linear array semantics for qubits."""
    QubitArray = guppy.type_alias("QubitArray", "array[qubit, 2]")

    @guppy
    def use_qubits(qs: QubitArray @ owned) -> int:
        q1, q2 = qs
        discard(q1)
        x(q2)
        return 1 if measure(q2) else 0

    @guppy
    def main() -> int:
        qs: QubitArray = array(qubit(), qubit())
        return use_qubits(qs)

    run_int_fn(main, expected=1, num_qubits=2)


def test_generic_struct_alias(run_int_fn):
    """Type aliases can refer to concrete instantiations of generic structs."""
    T = guppy.type_var("T")

    @guppy.struct
    class Box(Generic[T]):
        value: T

    IntBox = guppy.type_alias("IntBox", "Box[int]")

    @guppy
    def increment(box: IntBox) -> IntBox:
        return Box(box.value + 1)

    @guppy
    def main() -> int:
        box = increment(Box(41))
        return box.value

    run_int_fn(main, expected=42)


def test_explicit_generic_alias_single_param(run_int_fn):
    """Generic alias with a single explicit type param can be instantiated."""
    T = guppy.type_var("T")

    @guppy.struct
    class Wrapper(Generic[T]):
        item: T

    MyWrapper = guppy.type_alias("MyWrapper", "Wrapper[T]", params=[T])

    @guppy
    def make_int_wrapper(v: int) -> MyWrapper[int]:
        return Wrapper(v)

    @guppy
    def main() -> int:
        w = make_int_wrapper(7)
        return w.item

    run_int_fn(main, expected=7)


def test_explicit_generic_alias_two_params(run_int_fn):
    """Generic alias with two explicit params respects given param order."""
    A = guppy.type_var("A")
    B = guppy.type_var("B")

    @guppy.struct
    class Pair(Generic[A, B]):
        first: A
        second: B

    # Explicitly reverse the param order: Swap[X, Y] = Pair[Y, X]
    Swap = guppy.type_alias("Swap", "Pair[B, A]", params=[A, B])

    @guppy
    def main() -> int:
        # Swap[int, bool] → Pair[bool, int] so first is bool, second is int
        s: Swap[int, bool] = Pair(True, 42)
        return s.second

    run_int_fn(main, expected=42)


def test_implicit_generic_alias(run_int_fn):
    """When params is omitted, free vars are collected from body in appearance order."""
    T = guppy.type_var("T")

    @guppy.struct
    class Box(Generic[T]):
        value: T

    # No params= → T is a free var, collected automatically
    BoxAlias = guppy.type_alias("BoxAlias", "Box[T]")

    @guppy
    def get_value(b: BoxAlias[int]) -> int:
        return b.value

    @guppy
    def main() -> int:
        return get_value(Box(99))

    run_int_fn(main, expected=99)


def test_const_var_alias(run_int_fn):
    """Generic aliases can be parameterised by const variables."""
    B = guppy.const_var("B", "bool")

    @guppy.struct
    class Flagged(Generic[B]):
        value: int

    # Alias parameterised by a const var; resolved lazily when the alias is checked.
    MyFlagged = guppy.type_alias("MyFlagged", "Flagged[B]", params=[B])

    @guppy
    def get_value(f: MyFlagged[True]) -> int:
        return f.value

    @guppy
    def main() -> int:
        return get_value(Flagged(7))

    run_int_fn(main, expected=7)


# ---------------------------------------------------------------------------
# Struct / enum interaction tests
# ---------------------------------------------------------------------------


def test_alias_in_struct_field(run_int_fn):
    """A struct field can be typed with a concrete alias."""
    IntAlias = guppy.type_alias("IntAlias", "int")

    @guppy.struct
    class Point:
        x: IntAlias
        y: IntAlias

    @guppy
    def main() -> int:
        p = Point(3, 4)
        return p.x + p.y

    run_int_fn(main, expected=7)


def test_alias_of_struct(run_int_fn):
    """An alias can name a concrete struct type and be used transparently."""

    @guppy.struct
    class Vec2:
        x: int
        y: int

    VecAlias = guppy.type_alias("VecAlias", "Vec2")

    @guppy
    def dot(a: VecAlias, b: VecAlias) -> int:
        return a.x * b.x + a.y * b.y

    @guppy
    def main() -> int:
        return dot(Vec2(3, 4), Vec2(1, 2))

    run_int_fn(main, expected=11)


def test_generic_alias_in_struct_field(run_int_fn):
    """A generic alias used in a struct field is correctly expanded."""
    T = guppy.type_var("T")

    @guppy.struct
    class Box(Generic[T]):
        value: T

    Boxed = guppy.type_alias("Boxed", "Box[T]", params=[T])

    @guppy.struct
    class Outer:
        inner: Boxed[int]

    @guppy
    def main() -> int:
        o = Outer(Box(42))
        return o.inner.value

    run_int_fn(main, expected=42)


def test_alias_of_enum(validate):
    """An alias can name an enum type and be used in function signatures."""

    @guppy.enum
    class Color:
        Red = {}
        Green = {}
        Blue = {}

        @guppy
        def tag(self: "Color") -> int:
            return 0

    ColorAlias = guppy.type_alias("ColorAlias", "Color")

    @guppy
    def use_color(c: ColorAlias) -> int:
        return c.tag()

    @guppy
    def main() -> int:
        return use_color(Color.Red())

    validate(main.compile_function())


def test_alias_in_enum_variant_field(validate):
    """An enum variant field can be typed with an alias."""
    IntAlias = guppy.type_alias("IntAlias", "int")

    @guppy.enum
    class Msg:
        Value = {"n": IntAlias}
        Empty = {}

    @guppy
    def make_value(n: int) -> Msg:
        return Msg.Value(n)

    validate(make_value.compile_function())


def test_alias_as_type_arg_to_another_alias(validate):
    """A generic alias can be instantiated with another alias as the type argument."""
    T = guppy.type_var("T")

    @guppy.struct
    class Box(Generic[T]):
        value: T

    IntAlias = guppy.type_alias("IntAlias", "int")
    BoxOfIntAlias = guppy.type_alias("BoxOfIntAlias", "Box[IntAlias]")

    @guppy
    def make_box(x: int) -> BoxOfIntAlias:
        return Box(x)

    validate(make_box.compile_function())
