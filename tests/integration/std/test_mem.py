from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.mem import with_owned
from guppylang.std.quantum import qubit, measure


def test_with_owned(validate):
    @guppy
    def measure_and_reset(q: qubit) -> bool:
        def helper(q: qubit @ owned) -> tuple[bool, qubit]:
            return measure(q), qubit()

        return with_owned(q, helper)

    validate(measure_and_reset.compile_function())
