from guppylang.decorator import guppy
from guppylang.std.err import Result, ok, err
from guppylang.std.platform import result, panic
from guppylang.std.quantum import qubit  # noqa: TC002


def test_ok(run_int_fn):
    @guppy
    def main() -> int:
        x: Result[int, qubit] = ok(100)
        is_ok = 1 if x.is_ok() else 0
        is_err = 10 if x.is_err() else 0
        return is_ok + is_err + x.unwrap()

    run_int_fn(main, expected=101)


def test_err(run_int_fn):
    @guppy
    def main() -> int:
        x: Result[qubit, int] = err(100)
        is_ok = 1 if x.is_ok() else 0
        is_err = 10 if x.is_err() else 0
        return is_ok + is_err + x.unwrap_err()

    run_int_fn(main, expected=110)


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
        a: Result[int, tuple[int, int]] = err((1, 2))
        assertion(not a.is_ok() and a.is_err())
        a0, a1 = a.unwrap_err()
        result("a", a0 + a1)

        b: Result[tuple[int,], int] = ok((1,))
        assertion(b.is_ok() and not b.is_err())
        (b0,) = b.unwrap()
        result("b", b0)

        c: Result[(), int] = ok(())
        assertion(c.is_ok() and not c.is_err())
        () = c.unwrap()

        d: Result[int, None] = err(None)
        assertion(not d.is_ok() and d.is_err())
        d.unwrap_err()

    res = main.emulator(1).coinflip_sim().run().results[0].entries
    assert res == [("a", 3), ("b", 1)]
