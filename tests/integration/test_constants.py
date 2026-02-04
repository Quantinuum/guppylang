"""Constants are only loaded by execution compilers (not validation), test that."""

from guppylang.decorator import guppy
from guppylang.std.builtins import result, comptime


def test_basic_type(run_int_fn):
    @guppy.comptime
    def main() -> int:
        for x in [
            1,
            -1,
            0,
            1.2,
            -1.2,
            0.0,
            True,
            False,
            [1, 2, 3],
            [-1, -2, -3],
            [0, 0, 0],
            [1.2, 2.3, 3.4],
            [-1.2, -2.3, -3.4],
            [True, False, True],
        ]:
            result("x", x)
        return 0

    run_int_fn(main, 0)


def test_tuples(run_int_fn):
    # tuples cannot be `result` reported directly, so extract a value
    tup = (1, -1, 0, 1.2, -1.2, 0.0, True, False)

    @guppy
    def main() -> int:
        g_t = comptime(tup)
        x = g_t[0]
        result("x", x)
        return 0

    run_int_fn(main, 0)
