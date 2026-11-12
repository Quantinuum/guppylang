from guppylang.decorator import guppy
from guppylang.std.builtins import Function, owned
from guppylang.std.mem import mem_swap, with_owned
from guppylang.std.quantum import qubit, measure, Measurement


def test_mem_swap_copyable(run_int_fn):
    @guppy
    def main() -> int:
        x, y = 1, 2
        mem_swap(x, y)
        return 10 * x + y

    run_int_fn(main, expected=21)


def test_with_owned(validate):
    @guppy
    def measure_and_reset(q: qubit) -> Measurement:
        def helper(q: qubit @ owned) -> tuple[Measurement, qubit]:
            return measure(q), qubit()

        return with_owned(q, helper)

    validate(measure_and_reset.compile_function())


def test_with_owned_row(validate):
    @guppy
    def measure_and_reset(q: qubit) -> tuple[Measurement, int]:
        def helper(q: qubit @ owned) -> tuple[tuple[Measurement, int], qubit]:
            return (measure(q), 42), qubit()

        return with_owned(q, helper)

    validate(measure_and_reset.compile_function())


def test_borrowed_function_as_value_callback(run_int_fn):
    @guppy
    def exchange[T](x: T, y: T) -> None:
        mem_swap(x, y)

    @guppy
    def main() -> int:
        x, y = 1, 2
        callback: Function[[int, int], None] = exchange[int]
        callback(x, y)
        return 10 * x + y

    run_int_fn(main, expected=12)
