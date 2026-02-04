from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned


def test_turns_into_list(run_int_fn):
    @guppy.comptime
    def test(xs: array[int, 10]) -> int:
        assert isinstance(xs, list)
        assert len(xs) == 10

        return sum(xs)

    @guppy
    def main() -> int:
        return test(array(i for i in range(10)))

    run_int_fn(main, sum(range(10)))


def test_accepts_list(run_int_fn):
    @guppy
    def foo(xs: array[int, 10] @ owned) -> int:
        s = 0
        for x in xs:
            s += x
        return s

    @guppy.comptime
    def main() -> int:
        return foo(list(range(10)))

    run_int_fn(main, sum(range(10)))


def test_create(run_int_fn):
    @guppy.comptime
    def main() -> int:
        xs = array(*range(10))
        assert isinstance(xs, list)
        assert xs == list(range(10))
        return xs[-1]

    run_int_fn(main, 9)


def test_mutate(run_int_fn):
    @guppy.comptime
    def test(xs: array[int, 10]) -> None:
        ys = xs
        ys[0] = 100

    @guppy
    def main() -> int:
        xs = array(i for i in range(10))
        test(xs)
        return xs[0]

    run_int_fn(main, 100)


def test_comprehension(validate):
    @guppy.comptime
    def main() -> array[int, 5]:
        xs = array(i for i in range(5))
        assert xs == [0, 1, 2, 3, 4]
        return xs

    validate(main.compile_function())
