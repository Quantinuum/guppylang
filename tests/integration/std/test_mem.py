from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.mem import with_owned
from guppylang.std.quantum import qubit, measure, Measurement


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
