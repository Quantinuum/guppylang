from hugr import ops

from guppylang import comptime
from guppylang.decorator import guppy
from guppylang.std.builtins import array, owned
from guppylang.std.mem import mem_swap
from guppylang.std.num import nat
from guppylang.std.platform import result
from tests.util import compile_guppy

from guppylang.std.quantum import qubit, discard, measure, h, discard_array


def test_len_execute(validate, run_int_fn):
    @guppy
    def main(xs: array[float, 42]) -> int:
        return len(xs)

    validate(main.compile_function())
    run_int_fn(main, expected=42, args=[array(float(i) for i in range(42))])


def test_len_linear(validate):
    @guppy
    def main(qs: array[qubit, 42]) -> int:
        return len(qs)

    validate(main.compile_function())


def test_len_generic(validate):
    n = guppy.nat_var("n")

    @guppy
    def main(qs: array[bool, n]) -> bool:
        for i in range(len(qs)):
            if qs[i]:
                return True
        return False

    package = main.compile_function()
    validate(package)

    hg = package.modules[0]
    load_nats = [
        data.op
        for _, data in hg.nodes()
        if isinstance(data.op, ops.ExtOp) and data.op.op_def().name == "load_nat"
    ]
    assert len(load_nats) == 1


def test_index(validate):
    @compile_guppy
    def main(xs: array[int, 5], i: int) -> int:
        return xs[0] + xs[i] + xs[xs[2 * i]]

    validate(main)


def test_new_array(validate):
    @compile_guppy
    def main(x: int, y: int) -> array[int, 3]:
        xs = array(x, y, x)
        return xs

    validate(main)


def test_new_array_infer_empty(validate):
    @compile_guppy
    def main() -> array[float, 0]:
        return array()

    validate(main)


def test_new_array_infer_nested(validate):
    @compile_guppy
    def main(ys: array[int, 0] @ owned) -> array[array[int, 0], 2]:
        xs = array(ys, array())
        return xs

    validate(main)


def test_new_array_check_nested_length(validate):
    n = guppy.nat_var("n")

    @guppy
    def foo(xs: array[array[int, n], 1]) -> None:
        pass

    @guppy
    def main() -> None:
        foo(array(array(1, 2, 3)))

    validate(main.compile_function())


def test_return_linear_array(validate):
    @guppy
    def foo() -> array[qubit, 2]:
        a = array(qubit(), qubit())
        return a

    validate(foo.compile_function())


def test_subscript_drop_rest(validate):
    @guppy.declare
    def foo() -> array[int, 10]: ...

    @guppy
    def main() -> int:
        return foo()[0]

    validate(main.compile_function())


def test_linear_subscript(validate):
    @guppy.declare
    def foo(q: qubit) -> None: ...

    @guppy
    def main(qs: array[qubit, 42] @ owned, i: int) -> array[qubit, 42]:
        foo(qs[i])
        return qs

    validate(main.compile_function())


def test_inout_subscript(validate):
    @guppy.declare
    def foo(q: qubit) -> None: ...

    @guppy
    def main(qs: array[qubit, 42], i: int) -> None:
        foo(qs[i])

    validate(main.compile_function())


def test_multi_subscripts(validate):
    @guppy.declare
    def foo(q1: qubit, q2: qubit) -> None: ...

    @guppy
    def main(qs: array[qubit, 42] @ owned) -> array[qubit, 42]:
        foo(qs[0], qs[1])
        foo(qs[0], qs[0])  # Will panic at runtime
        return qs

    validate(main.compile_function())


def test_inout_subscript_coerce(validate):
    """See https://github.com/CQCL/guppylang/issues/1356"""

    @guppy.declare
    def foo(q: qubit) -> None: ...

    @guppy
    def main(qs: array[qubit, 42], i: nat) -> None:
        foo(qs[i])

    validate(main.compile_function())


def test_struct_array(validate):
    @guppy.struct
    class S:
        q1: qubit
        q2: qubit

    @guppy.declare
    def foo(q1: qubit, q2: qubit) -> None: ...

    @guppy
    def main(ss: array[S, 10] @ owned) -> array[S, 10]:
        # This will panic at runtime :(
        # To make this work, we would need to replace the qubits in the struct
        # with `qubit | None` and write back `None` after `q1` has been extracted...
        foo(ss[0].q1, ss[0].q2)
        return ss

    validate(main.compile_function())


def test_nested_subscripts(validate):
    @guppy.declare
    def foo(q: qubit) -> None: ...

    @guppy.declare
    def bar(q1: qubit, q2: qubit, q3: qubit, q4: qubit) -> None: ...

    @guppy
    def main(qs: array[array[qubit, 13], 42] @ owned) -> array[array[qubit, 13], 42]:
        foo(qs[0][0])
        # The following should work *without* panicking at runtime! Accessing `qs[0][0]`
        # replaces one qubit with `None` but puts everything back into `qs` before
        # going to the next argument.
        bar(qs[0][0], qs[0][1], qs[1][0], qs[1][1])
        return qs

    validate(main.compile_function())


def test_struct_nested_subscript(validate):
    @guppy.struct
    class C:
        c: qubit
        blah: int

    @guppy.struct
    class B:
        ys: array[array[C, 10], 20]
        foo: C

    @guppy.struct
    class A:
        xs: array[B, 42]
        bar: qubit
        baz: tuple[B, B]

    @guppy.declare
    def foo(q1: qubit) -> None: ...

    @guppy
    def main(a: A @ owned, i: int, j: int, k: int) -> A:
        foo(a.xs[i].ys[j][k].c)
        return a

    validate(main.compile_function())


def test_generic_function(validate):
    T = guppy.type_var("T", copyable=False, droppable=False)
    n = guppy.nat_var("n")

    @guppy
    def foo(xs: array[T, n] @ owned) -> array[T, n]:
        return xs

    @guppy
    def main() -> tuple[array[int, 3], array[qubit, 2]]:
        xs = array(1, 2, 3)
        ys = array(qubit(), qubit())
        return foo(xs), foo(ys)

    validate(main.compile_function())


def test_linear_for_loop(validate):
    @guppy
    def main() -> None:
        qs = array(qubit(), qubit(), qubit())
        for q in qs:
            discard(q)

    validate(main.compile_function())


def test_exec_array(run_int_fn):
    @guppy
    def main() -> int:
        a = array(1, 2, 3)
        return a[0] + a[1] + a[2]

    run_int_fn(main, expected=6)


def test_exec_array_loop(run_int_fn):
    @guppy
    def main() -> int:
        xs = array(1, 2, 3, 4, 5, 6, 7)
        s = 0
        for x in xs:
            if x % 2 == 0:
                continue
            if x > 5:
                break
            s += x
        return s

    run_int_fn(main, expected=9)


def test_mem_swap(validate):
    @guppy
    def foo(x: qubit, y: qubit) -> None:
        mem_swap(x, y)

    @guppy
    def main() -> array[qubit, 2]:
        a = array(qubit(), qubit())
        foo(a[0], a[1])
        return a

    package = main.compile_function()
    validate(package)


def test_drop(validate):
    @compile_guppy
    def main(xs: array[int, 2] @ owned) -> None:
        ys = xs

    validate(main)


def test_copy1(run_int_fn):
    @guppy
    def main() -> int:
        xs = array(1, 2, 3)
        ys = xs.copy()
        xs = array(4, 5, 6)
        return xs[0] + ys[0]  # Check copy isn't modified

    run_int_fn(main, expected=5)


def test_copy2(run_int_fn):
    @guppy
    def main() -> int:
        xs = array(1, 2, 3)
        ys = xs.copy()
        xs = array(4, 5, 6)
        return xs[0] + ys[0]  # Check copy isn't modified

    run_int_fn(main, expected=5)


def test_copy3(run_int_fn):
    @guppy
    def main() -> int:
        xs = array(1, 2, 3)
        ys = xs.copy()
        return xs[0]  # Check original can keep being used

    run_int_fn(main, expected=1)


def test_copy_struct(run_int_fn):
    @guppy.struct
    class S:
        a: array[int, 1]

    @guppy
    def main() -> int:
        xs = array(S(array(1)), S(array(2)))
        ys = xs[0].a.copy()
        return ys[0]

    run_int_fn(main, expected=1)


def test_copy_inside(run_int_fn):
    @guppy
    def main() -> int:
        xs = array(array(1), array(1))
        ys = xs[0].copy()
        return ys[0]

    run_int_fn(main, expected=1)


def test_copy_const(run_int_fn):
    @guppy
    def main() -> int:
        xs = array(1, 2, 3).copy()
        return xs[0]

    run_int_fn(main, expected=1)


def test_subscript_assign(run_int_fn):
    @guppy
    def foo(xs: array[int, 3] @ owned, idx: int, n: int) -> array[int, 3]:
        xs[idx] = n
        return xs

    @guppy
    def main() -> int:
        xs = array(0, 0, 0)
        xs = foo(xs, 0, 2)
        return xs[0]

    run_int_fn(main, expected=2)


def test_subscript_assign_add(run_int_fn):
    @guppy
    def foo(xs: array[int, 1], n: int) -> None:
        xs[0] += n

    @guppy
    def main() -> int:
        xs = array(0)
        for i in range(6):
            foo(xs, i)
        return xs[0]

    run_int_fn(main, expected=15)


def test_subscript_assign_struct(run_int_fn):
    @guppy.struct
    class S:
        a: array[int, 2]

    @guppy
    def foo(xs: array[int, 2], idx: int, n: int) -> None:
        xs[idx] = n

    @guppy
    def main() -> int:
        s = S(array(0, 0))
        foo(s.a, 1, 42)
        return s.a[1]

    run_int_fn(main, expected=42)


def test_subscript_assign_nested(run_int_fn):
    @guppy
    def foo(xs: array[array[int, 2], 2]) -> None:
        xs[0][0] = 22

    @guppy
    def main() -> int:
        xs = array(array(11, 11), array(11, 11))
        foo(xs)
        return xs[0][0]

    run_int_fn(main, expected=22)


def test_subscript_assign_nested_struct1(run_int_fn):
    @guppy.struct
    class S:
        a: array[int, 2]

    @guppy
    def main() -> int:
        s0 = S(array(0, 0))
        s1 = S(array(1, 1))
        arr = array(s0, s1)
        arr[0].a[1] = 42
        return arr[0].a[1]

    run_int_fn(main, expected=42)


def test_subscript_assign_nested_struct2(run_int_fn):
    @guppy.struct
    class A:
        b: array[int, 2]

    @guppy.struct
    class S:
        a: array[A, 2]

    @guppy
    def main() -> int:
        s0 = S(array(A(array(0, 0)), A(array(0, 0))))
        s1 = S(array(A(array(0, 0)), A(array(0, 0))))
        arr = array(s0, s1)
        arr[0].a[1].b = array(42, 42)
        arr[0].a[1].b[0] = 43
        return arr[0].a[1].b[0]

    run_int_fn(main, expected=43)


def test_subscript_assign_nested_struct3(run_int_fn):
    @guppy.struct
    class A:
        b: array[int, 2]

    @guppy.struct
    class S:
        a: A

    @guppy
    def main() -> int:
        s0 = S(A(array(0, 0)))
        s1 = S(A(array(0, 0)))
        arr = array(s0, s1)
        arr[0].a.b[0] = 2
        return arr[0].a.b[0]

    run_int_fn(main, expected=2)


def test_subscript_assign_nested_struct4(run_int_fn):
    @guppy.struct
    class S:
        xs: array[int, 1]

    @guppy
    def main() -> int:
        arr = array(S(array(0)), S(array(1)))
        arr[0].xs = array(3)
        return arr[0].xs[0]

    run_int_fn(main, expected=3)


def test_subscript_assign_nested_struct5(run_int_fn):
    @guppy.struct
    class A:
        b: array[int, 2]

    @guppy.struct
    class S:
        a: array[A, 2]

    @guppy
    def main() -> int:
        s0 = S(array(A(array(0, 0)), A(array(0, 0))))
        s1 = S(array(A(array(0, 0)), A(array(0, 0))))
        arr = array(s0, s1)
        arr[0].a[0].b = array(42, 42)
        return arr[0].a[0].b[0]

    run_int_fn(main, expected=42)


def test_subscript_assign_unpacking(run_int_fn):
    @guppy
    def main() -> int:
        xs = array(11, 22, 33)
        xs[0], y = 44, 55
        return xs[0]

    run_int_fn(main, expected=44)


def test_subscript_subscript_assign(run_int_fn):
    @guppy
    def main() -> int:
        xs = array(0)
        ys = array(1)
        xs[0] = ys[0]
        return xs[0]

    run_int_fn(main, expected=1)


def test_subscript_assign_unpacking_tuple(run_int_fn):
    @guppy
    def main() -> int:
        xs = array(0, 0, 0)
        a, *b, xs[1] = (1, 2, 3, 4)
        return xs[1]

    run_int_fn(main, expected=4)


def test_subscript_assign_unpacking_complicated(run_int_fn):
    @guppy
    def main() -> int:
        xs = array(0, 0, 0)
        (a1, _a2), *_b, (c1, _c2) = array((0, 1), (2, 3), (4, 5), (5, 6))
        return a1 + c1

    run_int_fn(main, expected=5)


def test_subscript_assign_unpacking_range(run_int_fn):
    @guppy
    def main() -> int:
        xs = array(0, 0, 0)
        _a, *_b, xs[1] = range(10)
        return xs[1]

    run_int_fn(main, expected=9)


def test_subscript_assign_unpacking_array(run_int_fn):
    @guppy
    def main() -> int:
        xs = array(0, 0, 0)
        _a, *_b, xs[1] = array(1, 2, 3, 4)
        return xs[1]

    run_int_fn(main, expected=4)


# Verifies that array.__getitem__ works across multiple functions calls.
def test_multiple_functions(run_int_fn):
    @guppy
    def first(arr: array[int, 2]) -> int:
        return arr[0]

    @guppy
    def second(arr: array[int, 2]) -> int:
        return arr[1]

    @guppy
    def main() -> int:
        xs = array(1, 2)
        return first(xs) + second(xs)

    run_int_fn(main, expected=3)


# Verifies that the same index in a classical array can be accessed twice.
def test_multiple_classical_accesses(run_int_fn):
    @guppy
    def main() -> int:
        xs = array(1, 2)
        return xs[0] + xs[0]

    run_int_fn(main, expected=2)


def test_assign_dataflow(validate):
    """Test that dataflow analysis considers subscript assignments as uses and correctly
    wires up the Hugr.

    See https://github.com/quantinuum/guppylang/issues/844
    """

    @guppy
    def test1() -> None:
        xs = array(1, 2)
        for i in range(2):
            xs[i] = 0

    @guppy
    def test2() -> None:
        xs = array(0, 1)
        ys = array(1, 2)
        for i in range(2):
            ys[xs[i]] = 0

    test1.compile_function()
    test2.compile_function()


def test_take_put(validate):
    @guppy
    def foo(q: qubit, x: None) -> None:
        pass

    @guppy
    def main() -> int:
        qs = array(qubit() for _ in range(10))
        result("init", qs.is_borrowed(3))  # False

        # Arguments are borrowed left to right
        foo(qs[3], result("while_borrowed", qs.is_borrowed(3)))  # True
        result("after_borrowed", qs.is_borrowed(3))  # False

        # We can't put stuff when it's not borrowed
        q = qubit()
        q = qs.try_put(q, 3).unwrap_err()
        discard(q)

        # We can't take out stuff that's already borrowed
        q = qs.take(3)
        result("after_take", qs.is_borrowed(3))  # True
        qs.try_take(3).unwrap_nothing()
        measure(q)

        # But we can put something back
        qs.put(qubit(), 3)
        result("after_put", qs.is_borrowed(3))  # False
        h(qs[3])

        discard_array(qs)
        return 0

    res = main.emulator(11).coinflip_sim().run().results[0].entries
    assert res == [
        ("init", 0),
        ("while_borrowed", 1),
        ("after_borrowed", 0),
        ("after_take", 1),
        ("after_put", 0),
    ]

    validate(main.compile())


# https://github.com/CQCL/hugr/issues/1826
def test_array_const(validate, run_int_fn):
    @guppy
    def main() -> int:
        bs = comptime([True, False])
        return int(bs[0])

    run_int_fn(main, expected=1)
