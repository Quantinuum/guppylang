import pytest

from guppylang import guppy
from guppylang.std.builtins import array, nat, output


def test_assign_integer_to_float_field(run_float_fn_approx):
    @guppy.struct
    class S:
        value: float

    @guppy
    def main() -> float:
        s = S(0.0)
        s.value = 42
        return s.value

    run_float_fn_approx(main, 42.0)


def test_unpack_to_float_fields(run_float_fn_approx):
    @guppy.struct
    class S:
        value: float

    @guppy
    def main() -> float:
        a, b = S(0.0), S(0.0)
        a.value, b.value = 2, 3
        return a.value + b.value

    run_float_fn_approx(main, 5.0)


def test_array_unpack_to_float_fields(run_float_fn_approx):
    @guppy.struct
    class S:
        value: float

    @guppy
    def main() -> float:
        a, b = S(0.0), S(0.0)
        a.value, b.value = array(2, 3)
        return a.value + b.value

    run_float_fn_approx(main, 5.0)


def test_nested_field_coercion(run_int_fn):
    @guppy.struct
    class Inner:
        value: int

    @guppy.struct
    class Outer:
        inner: Inner

    @guppy
    def main() -> int:
        s = Outer(Inner(0))
        n: nat = 4
        s.inner.value = n
        return s.inner.value

    run_int_fn(main, 4)


def test_iterable_unpack_to_float_fields(run_float_fn_approx):
    @guppy.struct
    class S:
        value: float

    @guppy
    def main() -> float:
        a, b = S(0.0), S(0.0)
        a.value, b.value = range(2)
        return a.value + b.value

    run_float_fn_approx(main, 1.0)


def test_annotated_field_assign(run_float_fn_approx):
    @guppy.struct
    class S:
        value: float

    @guppy
    def main() -> float:
        s = S(0.0)
        s.value: int = 42
        return s.value

    run_float_fn_approx(main, 42.0)


@pytest.mark.execution
def test_field_assignment_evaluates_rhs_once(target_platform):
    @guppy.struct
    class S:
        value: float

    @guppy
    def rhs() -> int:
        output("rhs", True)
        return 42

    @guppy
    def main() -> None:
        s = S(0.0)
        s.value = rhs()
        output("value", s.value)

    results = main.emulator(0, platform=target_platform).coinflip_sim().run()
    assert results.collated_shots() == [{"rhs": [True], "value": [42.0]}]


@pytest.mark.execution
def test_unpack_assignment_evaluates_rhs_once(target_platform):
    @guppy.struct
    class S:
        value: float

    @guppy
    def rhs() -> tuple[int, int]:
        output("rhs", True)
        return 2, 3

    @guppy
    def main() -> None:
        a, b = S(0.0), S(0.0)
        a.value, b.value = rhs()
        output("value", a.value + b.value)

    results = main.emulator(0, platform=target_platform).coinflip_sim().run()
    assert results.collated_shots() == [{"rhs": [True], "value": [5.0]}]


def test_coercion_does_not_allow_frozen_field_mutation():
    from guppylang_internals.error import GuppyTypeError

    @guppy.struct(frozen=True)
    class S:
        value: float

    @guppy
    def main() -> None:
        s = S(0.0)
        s.value = 42

    with pytest.raises(GuppyTypeError, match="immutable"):
        main.check()


def test_coercion_does_not_allow_narrowing():
    from guppylang_internals.error import GuppyTypeError

    @guppy.struct
    class S:
        value: int

    @guppy
    def main() -> None:
        s = S(0)
        s.value = 42.0

    with pytest.raises(GuppyTypeError, match="Type mismatch"):
        main.check()


def test_assign_function_item_to_function_field(run_int_fn):
    from guppylang.std.builtins import Function

    @guppy.struct
    class S:
        fn: Function[[int], int]

    @guppy
    def first(x: int) -> int:
        return x

    @guppy
    def second(x: int) -> int:
        return x + 1

    @guppy
    def main() -> int:
        s = S(first)
        s.fn = second
        return s.fn(42)

    run_int_fn(main, 43)


def test_assign_nat_to_float_field(run_float_fn_approx):
    @guppy.struct
    class S:
        value: float

    @guppy
    def main() -> float:
        s = S(0.0)
        n: nat = 42
        s.value = n
        return s.value

    run_float_fn_approx(main, 42.0)


def test_same_type_field_assignment(run_float_fn_approx):
    @guppy.struct
    class S:
        value: float

    @guppy
    def main() -> float:
        s = S(0.0)
        s.value = 42.0
        return s.value

    run_float_fn_approx(main, 42.0)


def test_coercion_does_not_allow_temporary_target():
    from guppylang_internals.error import GuppyError

    @guppy.struct
    class S:
        value: float

    @guppy
    def main() -> None:
        S(0.0).value = 42

    with pytest.raises(GuppyError, match="not supported"):
        main.check()


def test_loop_assign_to_float_field(run_float_fn_approx):
    @guppy.struct
    class S:
        value: float

    @guppy
    def main() -> float:
        s = S(0.0)
        for s.value in range(3):
            pass
        return s.value

    run_float_fn_approx(main, 2.0)
