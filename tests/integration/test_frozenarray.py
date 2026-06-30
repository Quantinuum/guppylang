from guppylang import guppy
from guppylang.std.builtins import frozenarray, panic

_RANGE_42 = list(range(42))
_NESTED_2X2 = [[1, 2], [3, 4]]


def test_len(run_int_fn):
    @guppy
    def foo(xs: frozenarray[int, 42]) -> int:
        return len(xs)

    @guppy
    def main() -> int:
        return foo(_RANGE_42)

    run_int_fn(main, 42)


def test_subscript(run_int_fn):
    @guppy
    def foo(xs: frozenarray[int, 42]) -> int:
        return xs[10] + xs[10]

    @guppy
    def main() -> int:
        return foo(_RANGE_42)

    run_int_fn(main, 20)


def test_iter(run_int_fn):
    @guppy
    def foo(xs: frozenarray[int, 42]) -> int:
        s = 0
        for x in xs:
            s += x
        return s

    @guppy
    def main() -> int:
        return foo(_RANGE_42)

    run_int_fn(main, sum(range(42)))


def test_alias(run_int_fn):
    @guppy
    def foo(xs: frozenarray[int, 42]) -> int:
        ys = xs
        return xs[0] + ys[1]

    @guppy
    def main() -> int:
        return foo(_RANGE_42)

    run_int_fn(main, 1)


def test_mutable_copy(run_int_fn):
    @guppy
    def foo(xs: frozenarray[int, 42]) -> int:
        ys = xs.mutable_copy()
        s = 0
        for i in range(42):
            if xs[i] != ys[i]:
                panic("Mismatch")
            s += xs[i]
            s += ys[i]
        return s

    @guppy
    def main() -> int:
        return foo(_RANGE_42)

    run_int_fn(main, 2 * sum(range(42)))


def test_nested_subscript(run_int_fn):
    @guppy
    def foo(xs: frozenarray[frozenarray[int, 2], 2]) -> int:
        return xs[0][0] + xs[0][1] + xs[1][0] + xs[1][1]

    @guppy
    def main() -> int:
        return foo(_NESTED_2X2)

    run_int_fn(main, 1 + 2 + 3 + 4)


def test_nested_iter(run_int_fn):
    @guppy
    def foo(xss: frozenarray[frozenarray[int, 10], 42]) -> int:
        s = 0
        for xs in xss:
            for x in xs:
                s += x
        return s

    xss = [[i * j for j in range(10)] for i in range(42)]

    @guppy
    def main() -> int:
        return foo(xss)

    run_int_fn(main, sum([sum(xs) for xs in xss]))


def test_nested_struct(validate):
    @guppy.struct(frozen=True)
    class S:
        xs: frozenarray[int, 10]
        y: int

    @guppy
    def foo(xss: frozenarray[S, 42]) -> int:
        s = xss[0].y + xss[0].xs[0]
        for ss in xss:
            for x in ss.xs:
                s += x
        return s

    validate(foo.compile_function())


def test_nested_enum(validate):
    @guppy.enum
    class E:
        VariantA = {"xe": frozenarray[int, 42]}

        @guppy
        def tag(self) -> int:
            return 1

    @guppy
    def foo(es: frozenarray[E, 42]) -> int:
        s = 0
        for e in es:
            s += e.tag()
        return s

    validate(foo.compile_function())
