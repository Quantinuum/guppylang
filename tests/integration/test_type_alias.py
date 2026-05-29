from typing import Generic

from guppylang import array, guppy, qubit
from guppylang.std.builtins import owned
from guppylang.std.quantum import discard, measure, x


def test_alias_chain(run_int_fn):
    """Type aliases can chain through other aliases for scalar types."""
    MyInt = guppy.type_alias("int")
    MyOtherInt = guppy.type_alias("MyInt")

    @guppy
    def main(x: MyOtherInt) -> MyInt:
        return x + 1

    run_int_fn(main, expected=42, args=[41])


def test_array_alias(validate):
    """Type aliases can name nested concrete array types."""
    Row = guppy.type_alias("array[int, 2]")
    Matrix = guppy.type_alias("array[Row, 2]")

    @guppy
    def main(xs: Matrix) -> int:
        return xs[0][0] + xs[0][1] + xs[1][0] + xs[1][1]

    validate(main.compile_function())


def test_qubit_array_alias(run_int_fn):
    """Type aliases preserve owned linear array semantics for qubits."""
    QubitArray = guppy.type_alias("array[qubit, 2]")

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

    IntBox = guppy.type_alias("Box[int]")

    @guppy
    def increment(box: IntBox) -> IntBox:
        return Box(box.value + 1)

    @guppy
    def main() -> int:
        box = increment(Box(41))
        return box.value

    run_int_fn(main, expected=42)
