from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned
from guppylang.std.quantum import qubit

from tests.util import compile_guppy


def test_basic_exec(run_int_fn):
    @guppy
    def test() -> array[int, 10]:
        return array(i + 1 for i in range(10))

    @guppy
    def main() -> int:
        s = 0
        for x in test():
            s += x
        return s

    run_int_fn(main, expected=sum(i + 1 for i in range(10)))


def test_basic_linear(validate):
    @guppy
    def test() -> array[qubit, 42]:
        return array(qubit() for _ in range(42))

    validate(test.compile_function())


def test_zero_length(run_int_fn):
    @guppy
    def test() -> array[float, 0]:
        return array(i / 0 for i in range(0))

    @guppy
    def main() -> int:
        test()
        return 0

    run_int_fn(main, expected=0)


def test_capture(run_int_fn):
    @guppy
    def test(x: int) -> array[int, 42]:
        return array(i + x for i in range(42))

    @guppy
    def main() -> int:
        s = 0
        for x in test(3):
            s += x
        return s

    run_int_fn(main, expected=sum(i + 3 for i in range(42)))


def test_capture_struct(validate):
    @guppy.struct
    class MyStruct:
        x: int
        y: float

    @guppy
    def test(s: MyStruct) -> array[int, 42]:
        return array(i + s.x for i in range(42))

    validate(test.compile_function())


def test_scope(validate):
    @compile_guppy
    def test() -> float:
        x = 42.0
        array(x for x in range(10))
        return x

    validate(test)


def test_nested_left(run_int_fn):
    @guppy
    def test() -> array[array[int, 10], 20]:
        return array(array(x + y for y in range(10)) for x in range(20))

    @guppy
    def main() -> int:
        s = 0
        for xs in test():
            for x in xs:
                s += x
        return s

    run_int_fn(main, expected=sum(x + y for y in range(10) for x in range(20)))


def test_generic_size(validate):
    n = guppy.nat_var("n")

    @guppy
    def test(xs: array[int, n] @ owned) -> array[int, n]:
        return array(x + 1 for x in xs)

    validate(test.compile_function())


def test_generic_elem(validate):
    T = guppy.type_var("T")

    @guppy
    def foo(x: T) -> array[T, 10]:
        return array(x for _ in range(10))

    validate(foo.compile_function())


def test_borrow(validate):
    n = guppy.nat_var("n")

    @guppy.declare
    def foo(q: qubit) -> int: ...

    @guppy
    def test(q: qubit) -> array[int, n]:
        return array(foo(q) for _ in range(n))

    validate(test.compile_function())


def test_borrow_twice(validate):
    n = guppy.nat_var("n")

    @guppy.declare
    def foo(q: qubit) -> int: ...

    @guppy
    def test(q: qubit) -> array[int, n]:
        return array(foo(q) + foo(q) for _ in range(n))

    validate(test.compile_function())


def test_borrow_struct(validate):
    n = guppy.nat_var("n")

    @guppy.struct
    class MyStruct:
        q1: qubit
        q2: qubit

    @guppy.declare
    def foo(s: MyStruct) -> int: ...

    @guppy
    def test(s: MyStruct) -> array[int, n]:
        return array(foo(s) for _ in range(n))

    validate(test.compile_function())


def test_borrow_and_consume(validate):
    n = guppy.nat_var("n")

    @guppy.declare
    def foo(q: qubit) -> int: ...

    @guppy.declare
    def bar(q: qubit @ owned) -> int: ...

    @guppy
    def test(qs: array[qubit, n] @ owned) -> array[int, n]:
        return array(foo(q) + bar(q) for q in qs)

    validate(test.compile_function())
