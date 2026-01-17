from typing import no_type_check

from guppylang import guppy
from guppylang.std.builtins import array, owned
from guppylang.std.debug import state_result
from guppylang.std.quantum import qubit, discard, discard_array, x, h, cx
from tests.util import compile_guppy


def test_basic(validate):
    @compile_guppy
    def main() -> None:
        q1 = qubit()
        q2 = qubit()
        state_result("tag", q1, q2)
        discard(q1)
        discard(q2)

    validate(main)


def test_multi(validate):
    @compile_guppy
    def main() -> None:
        q1 = qubit()
        q2 = qubit()
        state_result("tag1", q1, q2)
        x(q1)
        state_result("tag2", q1)
        discard(q1)
        discard(q2)

    validate(main)


def test_array_access(validate):
    @compile_guppy
    def main() -> None:
        qs = array(qubit() for _ in range(4))
        h(qs[1])
        h(qs[2])
        state_result("a", qs[1], qs[2], qs[3])
        state_result("b", qs[1])
        h(qs[3])

        cx(qs[1], qs[2])
        state_result("c", qs[2], qs[3])
        # cx(qs[3], qs[4]) #IndexOutOfBoundsError here...
        discard_array(qs)

    validate(main)


def test_struct_access(validate):
    @guppy.struct
    class S:
        q1: qubit
        q2: qubit
        q3: qubit
        q4: qubit

    @guppy
    @no_type_check
    def test(qs: S @ owned) -> None:
        h(qs.q1)
        h(qs.q2)
        state_result("1", qs.q1, qs.q2, qs.q3)
        state_result("2", qs.q1)
        h(qs.q3)

        cx(qs.q1, qs.q2)
        state_result("3", qs.q2, qs.q3)
        cx(qs.q3, qs.q4)

        discard(qs.q1)
        discard(qs.q2)
        discard(qs.q3)
        discard(qs.q4)

    validate(test.compile_function())


def test_array(validate):
    @compile_guppy
    def main() -> None:
        qs = array(qubit() for _ in range(4))
        h(qs[1])
        h(qs[2])
        cx(qs[0], qs[3])
        state_result("tag", qs)
        discard_array(qs)

    validate(main)


def test_generic_array(validate):
    n = guppy.nat_var("n")

    @guppy
    def main(qs: array[qubit, n]) -> None:
        cx(qs[0], qs[1])
        state_result("tag", qs)

    validate(main.compile_function())
