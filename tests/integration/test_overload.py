from guppylang import qubit, array
from guppylang.decorator import guppy
from guppylang_internals.decorator import custom_function, hugr_op
from guppylang_internals.definition.custom import NoopCompiler
from guppylang_internals.std._internal.util import int_op
from pytket import Circuit


def test_basic_overload(validate):
    @guppy.declare
    def variant1(x: float) -> None: ...

    @guppy.declare
    def variant2(x: int, y: int) -> None: ...

    @guppy.declare
    def variant3(x: int, y: int, z: int) -> None: ...

    @guppy.overload(variant1, variant2, variant3)
    def combined(*args): ...

    @guppy
    def main() -> None:
        combined(4.2)
        combined(1, 2)
        combined(1, 2, 3)

    validate(main.compile_function())


def test_pick_first(validate):
    """Check that we pick the first matching implementation, even if there are other
    matching ones coming afterwards.
    """

    @guppy.declare
    def variant1(x: float) -> int: ...

    @guppy.declare
    def variant2(x: int) -> None: ...

    @guppy.overload(variant1, variant2)
    def combined(*args): ...

    @guppy
    def main() -> int:
        x = combined(42)
        return x

    validate(main.compile_function())


def test_generic_overload(validate):
    S = guppy.type_var("S")
    T = guppy.type_var("T")

    @guppy.declare
    def variant1(x: T, y: T) -> float: ...

    @guppy.declare
    def variant2(x: T, y: S) -> int: ...

    @guppy.overload(variant1, variant2)
    def combined(*args): ...

    @guppy
    def main() -> int:
        # Check that we pick `variant2` since `variant1` doesn't match (the two args
        # would need to have the same type)
        x = combined(1, 1.0)
        return x

    validate(main.compile_function())


def test_pick_by_return_type1(validate):
    @guppy.declare
    def variant1() -> int: ...

    @guppy.declare
    def variant2() -> None: ...

    @guppy.overload(variant1, variant2)
    def combined(*args): ...

    @guppy
    def main() -> None:
        out: int = combined()

    validate(main.compile_function())


def test_pick_by_return_type2(validate):
    T = guppy.type_var("T")

    @guppy.declare
    def variant1(x: T) -> T: ...

    @guppy.declare
    def variant2(x: float) -> int: ...

    @guppy.overload(variant1, variant2)
    def combined(*args): ...

    @guppy
    def main() -> None:
        # Test that we're smart enough to pick variant2. A naive implementation would
        # match `variant1: float -> float` but then fail since it doesn't satisfy the
        # `out: float` annotation. Instead, we consider the whole signature including
        # the return type and infer that `variant2` is the only matching one.
        out: int = combined(42.0)

    validate(main.compile_function())


def test_comptime_overload_call(validate):
    """Check that overloaded calls work in comptime functions"""

    @guppy.declare
    def variant1(x: float) -> None: ...

    @guppy.declare
    def variant2(x: int, y: int) -> None: ...

    @guppy.declare
    def variant3(x: int, y: int, z: int) -> None: ...

    @guppy.overload(variant1, variant2, variant3)
    def combined(*args): ...

    @guppy.comptime
    def main() -> None:
        combined(4.2)
        combined(1, 2)
        combined(1, 2, 3)

    validate(main.compile_function())


def test_everything_can_be_overloaded(validate):
    """Test that all kinds of functions can be overloaded."""

    @custom_function(NoopCompiler())
    def custom(a: int) -> int: ...

    @hugr_op(int_op("iadd"))
    def my_hugr_op(a: int, b: int) -> int: ...

    @guppy.declare
    def declaration(a: int, b: int, c: int) -> None: ...

    @guppy
    def defined(a: int, b: int, c: int, d: int) -> int:
        return a + b + c + d

    @guppy.overload(declaration, defined)
    def overloaded(): ...  # Overloaded functions can be overloaded themselves!

    @guppy.overload(custom, my_hugr_op, declaration, defined, overloaded)
    def combined(): ...

    @guppy
    def main() -> None:
        combined(1)
        combined(1, 2)
        combined(1, 2, 3)
        combined(1, 2, 3, 4)

    validate(main.compile_function())

    # Test overloading circuits
    circ = Circuit(1)
    circ.H(0)

    @guppy.pytket(circ)
    def circ1(q: qubit) -> None: ...

    circ2 = guppy.load_pytket("circ2", circ, use_arrays=True)

    @guppy.overload(custom, my_hugr_op, declaration, defined, overloaded, circ1, circ2)
    def combined_circ(): ...

    @guppy
    def main(q: qubit, qs: array[qubit, 1]) -> None:
        combined_circ(1)
        combined_circ(1, 2)
        combined_circ(1, 2, 3)
        combined_circ(1, 2, 3, 4)
        combined_circ(q)
        combined_circ(qs)

    validate(main.compile_function())
