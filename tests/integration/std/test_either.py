from guppylang.decorator import guppy
from guppylang.std.array import array
from guppylang.std.either import Either, left, right
from guppylang.std.platform import panic, result
from guppylang.std.quantum import qubit  # noqa: TC002


def test_left(run_int_fn):
    @guppy
    def main() -> int:
        x: Either[int, qubit] = left(100)
        is_left = 1 if x.is_left() else 0
        is_right = 10 if x.is_right() else 0
        return is_left + is_right + x.unwrap_left()

    run_int_fn(main, expected=101)


def test_right(run_int_fn):
    @guppy
    def main() -> int:
        x: Either[qubit, int] = right(100)
        is_left = 1 if x.is_left() else 0
        is_right = 10 if x.is_right() else 0
        return is_left + is_right + x.unwrap_right()

    run_int_fn(main, expected=110)


def test_to_option(run_int_fn):
    @guppy
    def main() -> int:
        l_val: Either[int, float] = left(1)
        r_val: Either[float, int] = right(10)
        l_val.try_into_right().unwrap_nothing()
        r_val.try_into_left().unwrap_nothing()
        return l_val.try_into_left().unwrap() + r_val.try_into_right().unwrap()

    run_int_fn(main, expected=11)


def test_rows():
    """Make sure that Hugr generations correctly handles rows inside sums.

    See https://github.com/Quantinuum/guppylang/issues/1388
    """

    @guppy
    def assertion(b: bool) -> None:
        if not b:
            panic("Assertion failed!")

    @guppy
    def main() -> None:
        a: Either[int, tuple[int, int]] = right((1, 2))
        assertion(not a.is_left() and a.is_right())
        a0, a1 = a.unwrap_right()
        result("a", a0 + a1)

        b: Either[tuple[int,], int] = left((1,))
        assertion(b.is_left() and not b.is_right())
        (b0,) = b.unwrap_left()
        result("b", b0)

        c: Either[(), int] = left(())
        assertion(c.is_left() and not c.is_right())
        () = c.unwrap_left()

        d: Either[int, None] = right(None)
        assertion(not d.is_left() and d.is_right())
        d.unwrap_right()

    res = main.emulator(1).coinflip_sim().run().results[0].entries
    assert res == [("a", 3), ("b", 1)]


def test_either_comprehension(validate):
    @guppy
    def main(b: bool) -> Either[array[int, 3], int]:
        if b:
            return left(array(42 for x in range(3)))
        else:
            return right(0)

    validate(main.compile_function())
