import pytest

from guppylang import guppy
from guppylang.std.builtins import array, comptime, nat, output, result
from tests.util import compile_guppy


def test_basic(validate):
    @compile_guppy
    def main(x: int) -> None:
        output("foo", x)

    validate(main)


def test_multi(validate):
    @compile_guppy
    def main(w: nat, x: int, y: float, z: bool) -> None:
        output("a", w)
        output("b", x)
        output("c", y)
        output("d", z)

    validate(main)


def test_array(validate):
    @compile_guppy
    def main(
        w: array[nat, 42], x: array[int, 5], y: array[float, 1], z: array[bool, 0]
    ) -> None:
        output("a", w)
        output("b", x)
        output("c", y)
        output("d", z)

    validate(main)


# This caused problems with hugr (see https://github.com/Quantinuum/hugr/pull/2779),
# as it makes the linearizer copy an array (indeed, two arrays of different lengths).
def test_array_consts(run_int_fn):
    @guppy
    def main() -> int:
        output("x", array(True, False))
        output("y", array(False, True, False, False, True))
        return 3

    run_int_fn(main, 3)


def test_array_generic(validate):
    n = guppy.nat_var("n")

    @guppy
    def foo(
        w: array[nat, n], x: array[int, n], y: array[float, n], z: array[bool, n]
    ) -> None:
        output("a", w)
        output("b", x)
        output("c", y)
        output("d", z)

    @guppy
    def main(
        w: array[nat, 10], x: array[int, 10], y: array[float, 10], z: array[bool, 10]
    ) -> None:
        foo(w, x, y, z)

    validate(main.compile_function())


def test_array_drop_after_output(validate):
    @compile_guppy
    def main() -> None:
        output("a", array(1, 2, 3))

    validate(main)


def test_same_tag(validate):
    @compile_guppy
    def main(x: int, y: float, z: bool) -> None:
        output("foo", x)
        output("foo", y)
        output("foo", z)

    validate(main)


def test_comptime_tag_inside(validate):
    @compile_guppy
    def main(x: int) -> None:
        output(comptime("a" + "b"), x)

    validate(main)


def test_comptime_tag_outside1(validate):
    EXAMPLE_RESULTS = [
        ("boolean", False),
        ("int", 123),
    ]

    @guppy.comptime
    def main() -> None:
        for key, value in EXAMPLE_RESULTS:
            output(key, value)

    validate(main.compile_function())


def test_comptime_tag_outside2(validate):
    EXAMPLE_RESULT = ("boolean", False)

    @guppy.comptime
    def main() -> None:
        output(EXAMPLE_RESULT[0], EXAMPLE_RESULT[1])

    validate(main.compile_function())


def test_comptime_static_array_preserved_after_output(validate):
    @guppy.comptime
    def main() -> int:
        xs = array(1, 2)
        output("xs", xs)

        assert xs == [1, 2]
        return xs[0] + xs[1]

    validate(main.compile_function())


def test_comptime_dynamic_array_preserved_after_output(validate):
    @guppy
    def add_one(x: int) -> int:
        return x + 1

    @guppy.comptime
    def main(x: int) -> int:
        xs = array(add_one(x), 2)
        output("xs", xs)
        return xs[0] + xs[1]

    validate(main.compile_function())


def test_deprecated_result_alias_still_compiles(validate):
    @compile_guppy
    def main(x: int) -> None:
        result("foo", x)

    validate(main)


def test_scalar_numeric_output_ops(validate):
    from hugr import ops

    @guppy
    def main(w: nat, x: int, y: float, z: bool) -> None:
        output("nat", w)
        output("int", x)
        output("float", y)
        output("bool", z)

    package = main.with_minimal_opt().compile_function()
    validate(package)
    names = [
        data.op.op_def().name
        for _, data in package.modules[0].nodes()
        if isinstance(data.op, ops.ExtOp)
        and data.op.op_def().name.startswith("result_")
    ]
    assert names == ["result_uint", "result_int", "result_f64", "result_bool"]


def test_output_integer_literal_remains_signed(validate):
    from hugr import ops

    @guppy
    def main() -> None:
        output("literal", 1)

    package = main.with_minimal_opt().compile()
    validate(package)
    names = [
        data.op.op_def().name
        for _, data in package.modules[0].nodes()
        if isinstance(data.op, ops.ExtOp)
        and data.op.op_def().name.startswith("result_")
    ]
    assert names == ["result_int"]


@pytest.mark.execution
def test_output_max_nat(target_platform):
    @guppy
    def main() -> None:
        value: nat = 18446744073709551615
        output("value", value)

    results = main.emulator(0, platform=target_platform).coinflip_sim().run()
    assert results.collated_shots() == [{"value": [18446744073709551615]}]


@pytest.mark.execution
def test_output_max_nat_array_item(target_platform):
    @guppy
    def main() -> None:
        value: nat = 18446744073709551615
        values = array(value)
        output("value", values[0])

    results = main.emulator(0, platform=target_platform).coinflip_sim().run()
    assert results.collated_shots() == [{"value": [18446744073709551615]}]


@pytest.mark.execution
def test_output_max_nat_array(target_platform):
    @guppy
    def main() -> None:
        value: nat = 18446744073709551615
        values = array(value)
        output("values", values)

    results = main.emulator(0, platform=target_platform).coinflip_sim().run()
    assert results.collated_shots() == [{"values": [[18446744073709551615]]}]


@pytest.mark.execution
def test_output_checked_nat_result(target_platform):
    @guppy
    def main() -> None:
        value: nat = 18446744073709551615
        result: None = output("value", value)

    results = main.emulator(0, platform=target_platform).coinflip_sim().run()
    assert results.collated_shots() == [{"value": [18446744073709551615]}]


def test_output_negative_int(run_int_fn):
    @guppy
    def main() -> int:
        value = -1
        output("value", value)
        return value

    run_int_fn(main, -1)


@pytest.mark.execution
def test_output_nat_call_evaluated_once(target_platform):
    @guppy
    def value() -> nat:
        output("called", True)
        return 18446744073709551615

    @guppy
    def main() -> None:
        output("value", value())

    results = main.emulator(0, platform=target_platform).coinflip_sim().run()
    assert results.collated_shots() == [
        {"called": [True], "value": [18446744073709551615]}
    ]
