from tests.util import compile_guppy


def test_basic(validate):
    @compile_guppy
    def foo(xs: list[int]) -> int:
        for x in xs:
            pass
        return 0

    validate(foo)


def test_counting_loop(validate):
    @compile_guppy
    def foo(xs: list[int]) -> int:
        s = 0
        for x in xs:
            s += x
        return s

    validate(foo)


def test_multi_targets(validate):
    @compile_guppy
    def foo(xs: list[tuple[int, float]]) -> float:
        s = 0.0
        for x, y in xs:
            s += x * y
        return s

    validate(foo)


def test_multi_targets_same(validate):
    @compile_guppy
    def foo(xs: list[tuple[int, float]]) -> float:
        s = 1.0
        for x, x in xs:
            s *= x
        return s

    validate(foo)


def test_reassign_iter(validate):
    @compile_guppy
    def foo(xs: list[int]) -> int:
        s = 1
        for x in xs:
            xs = False
            s += x
        return s

    validate(foo)


def test_break(validate):
    @compile_guppy
    def foo(xs: list[int]) -> int:
        i = 1
        for x in xs:
            if x >= 42:
                break
            i *= x
        return i

    validate(foo)


def test_continue(validate):
    @compile_guppy
    def foo(xs: list[int]) -> int:
        i = len(xs)
        for x in xs:
            if x >= 42:
                continue
            i -= 1
        return i

    validate(foo)


def test_return_in_loop(validate):
    @compile_guppy
    def foo(xs: list[int]) -> int:
        y = 42
        for x in xs:
            if x >= 1337:
                return x * y
            y = y + x
        return y

    validate(foo)


def test_nested_loop(validate):
    @compile_guppy
    def foo(xs: list[int], ys: list[int]) -> int:
        p = 0
        for x in xs:
            s = 0
            for y in ys:
                s += y * x
            p += s - x
        return p

    validate(foo)


def test_nested_loop_break_continue(validate):
    @compile_guppy
    def foo(xs: list[int], ys: list[int]) -> int:
        p = 0
        for x in xs:
            s = 0
            for y in ys:
                if x % 2 == 0:
                    continue
                s += x
                if s > y:
                    s = y
                else:
                    break
            p += s * x
        return p

    validate(foo)


def test_loop_multiline_args(validate):
    @compile_guppy
    def foo() -> None:
        for _ in range(
            1
        ):  # fmt: skip
            pass

    validate(foo)
