from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned

from guppylang.std.quantum import qubit


def test_unpack_array(validate):
    @guppy
    def main(qs: array[qubit, 3] @ owned) -> tuple[qubit, qubit, qubit]:
        q1, q2, q3 = qs
        return q1, q2, q3

    validate(main.compile_function())


def test_unpack_starred(validate):
    @guppy
    def main(
        qs: array[qubit, 10] @ owned,
    ) -> tuple[qubit, qubit, qubit, qubit, qubit, qubit, array[qubit, 4]]:
        q1, q2, *qs, q3 = qs
        [q4, *qs] = qs
        *qs, q5, q6 = qs
        [*qs] = qs
        return q1, q2, q3, q4, q5, q6, qs

    validate(main.compile_function())


def test_unpack_starred_empty(validate):
    @guppy
    def main(qs: array[qubit, 2] @ owned) -> tuple[qubit, array[qubit, 0], qubit]:
        q1, *empty, q2 = qs
        return q1, empty, q2

    validate(main.compile_function())


def test_unpack_big_iterable(validate):
    # Test that the compile-time doesn't scale with the size of the unpacked iterable

    @guppy
    def main(qs: array[qubit, 1000] @ owned) -> tuple[qubit, array[qubit, 998], qubit]:
        q1, *qs, q2 = qs
        return q1, qs, q2

    validate(main.compile_function())


def test_unpack_range(run_int_fn):
    @guppy
    def main() -> int:
        [_, x, *_, y, _] = range(10)
        return x + y

    run_int_fn(main, expected=9)


def test_unpack_tuple_starred(validate):
    @guppy
    def main() -> array[int, 2]:
        x, *ys, z = 1, 2, 3, 4
        return ys

    validate(main.compile_function())


def test_unpack_nested(validate):
    @guppy
    def main(
        xs: array[array[array[int, 5], 10], 20] @ owned,
    ) -> tuple[
        array[int, 5],  # x
        int,  # y
        array[int, 3],  # z
        array[array[int, 5], 8],  # a
        array[array[array[int, 5], 10], 18],  # b
        array[array[int, 5], 10],  # c
    ]:
        (x, [y, *z, _], *a), *b, c = xs
        return x, y, z, a, b, c

    validate(main.compile_function())


def test_left_to_right(run_int_fn):
    @guppy
    def left() -> int:
        [x, x, *_] = range(10)
        return x

    @guppy
    def right() -> int:
        [*_, x, x] = range(10)
        return x

    run_int_fn(left, expected=1)

    run_int_fn(right, expected=9)
