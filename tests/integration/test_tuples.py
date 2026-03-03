from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned
from guppylang.std.mem import mem_swap
from guppylang.std.quantum import qubit, discard, h, x


def test_indexing(run_int_fn):
    @guppy
    def main() -> int:
        t = (0.2, 2, 2.2)
        x = t[1]
        return x

    run_int_fn(main, 2)


def test_indexing_input(validate):
    @guppy
    def main(t: tuple[int, float]) -> int:
        return t[0]

    validate(main.compile_function())


def test_indexing_drop(run_int_fn):
    @guppy
    def main() -> int:
        return (1, 2, 3)[2]

    run_int_fn(main, 3)


def test_indexing_drop2(validate):
    @guppy
    def main() -> qubit:
        return (1, 2, qubit())[2]

    validate(main.compile_function())


def test_indexing_nesting(run_int_fn):
    @guppy
    def main() -> int:
        t = (1, 2, (3, 4))
        return t[2][0]

    run_int_fn(main, 3)


def test_indexing_struct(run_int_fn):
    @guppy.struct
    class S:
        t: tuple[array[tuple[int, int], 1], int]

    @guppy
    def main() -> int:
        s = S((array((1, 2)), 3))
        return s.t[0][0][0] + 1

    run_int_fn(main, 2)


def test_rest_after_use(validate):
    @guppy.declare
    def use(x: qubit @ owned) -> None: ...

    @guppy
    def main() -> int:
        t = (1, qubit())
        use(t[1])
        return t[0]

    validate(main.compile_function())


def test_control_flow(validate):
    @guppy
    def foo(b: bool) -> None:
        t = (qubit(), qubit(), 0)
        if b:
            h(t[0])
        else:
            h(t[1])
        discard(t[0])
        discard(t[1])

    validate(foo.compile_function())


def test_control_flow2(validate):
    @guppy
    def foo() -> None:
        ts = array((qubit(), qubit()))
        h(ts[0][0])
        h(ts[0][1])
        for q1, q2 in ts:
            discard(q1)
            discard(q2)

    validate(foo.compile_function())


def test_mem_swap(validate):
    @guppy
    def foo(b: bool) -> None:
        t = (qubit(), qubit(), 0)
        if b:
            q = qubit()
            mem_swap(t[0], q)
            discard(q)
        else:
            q = qubit()
            mem_swap(t[1], q)
            discard(q)
        h(t[0])
        discard(t[0])
        discard(t[1])

    validate(foo.compile_function())


def test_non_terminating(validate):
    @guppy
    def foo(t: tuple[qubit, qubit, int]) -> None:
        while True:
            x(t[0])

    validate(foo.compile_function())
