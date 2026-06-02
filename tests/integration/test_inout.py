from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


def test_basic(validate):
    @guppy.declare
    def foo(q: qubit) -> None: ...

    @guppy
    def test(q: qubit @ owned) -> qubit:
        foo(q)
        return q

    validate(test.compile_function())


def test_mixed(validate):
    @guppy.declare
    def foo(q1: qubit, q2: qubit @ owned) -> qubit: ...

    @guppy
    def test(q1: qubit @ owned, q2: qubit @ owned) -> tuple[qubit, qubit]:
        q2 = foo(q1, q2)
        return q1, q2

    validate(test.compile_function())


def test_local(validate):
    @guppy.declare
    def foo(q: qubit) -> None: ...

    @guppy
    def test(q: qubit @ owned) -> qubit:
        f = foo
        f(q)
        return q

    validate(test.compile_function())


def test_nested_calls(validate):
    @guppy.declare
    def foo(x: int, q: qubit) -> int: ...

    @guppy
    def test(q: qubit @ owned) -> tuple[int, qubit]:
        # This is legal since function arguments and tuples are evaluated left to right
        return foo(foo(foo(0, q), q), q), q

    validate(test.compile_function())


def test_struct(validate):
    @guppy.struct
    class MyStruct:
        q1: qubit
        q2: qubit

    @guppy.declare
    def foo(q1: qubit, q2: qubit) -> None: ...

    @guppy.declare
    def bar(a: MyStruct) -> None: ...

    @guppy
    def test1(a: MyStruct @ owned) -> MyStruct:
        foo(a.q1, a.q2)
        bar(a)
        return a

    @guppy
    def test2(a: MyStruct @ owned) -> MyStruct:
        bar(a)
        foo(a.q1, a.q2)
        bar(a)
        return a

    validate(test1.compile_function())
    validate(test2.compile_function())


def test_control_flow(validate):
    @guppy.declare
    def foo(q: qubit) -> None: ...

    @guppy.declare
    def bar(q: qubit) -> bool: ...

    @guppy
    def test(q1: qubit @ owned, q2: qubit @ owned, n: int) -> tuple[qubit, qubit]:
        i = 0
        while i < n:
            foo(q1)
            if bar(q1) or bar(q2):
                foo(q2)
                continue
            elif not bar(q2):
                return q1, q2
            foo(q1)
            if bar(q2):
                foo(q1)
                break
            else:
                foo(q2)
            foo(q2)
            foo(q1)
            if bar(q2) and bar(q1):
                if i > 5:
                    foo(q2)
                return q1, q2
            foo(q1)
            i += 1
        return q1, q2

    validate(test.compile_function())


def test_tensor(validate):
    @guppy.struct
    class A:
        q: qubit

    @guppy.struct
    class B:
        q: qubit
        x: int

    @guppy.struct
    class C:
        q: qubit
        x: float

    @guppy.declare
    def foo(a: A, x: int) -> None: ...

    @guppy.declare
    def bar(y: float, b: B, c: C @ owned) -> C: ...

    @guppy.declare
    def baz(c: C) -> None: ...

    @guppy
    def test(
        a: A @ owned, b: B @ owned, c1: C @ owned, c2: C @ owned, x: bool
    ) -> tuple[A, B, C, C]:
        c1 = (foo, bar, baz)(a, b.x, c1.x, b, c1, c2)
        if x:
            c1 = ((foo, bar), baz)(a, b.x, c1.x, b, c1, c2)
        c1 = (foo, (bar, baz))(a, b.x, c1.x, b, c1, c2)
        return a, b, c1, c2

    validate(test.compile_function())


def test_basic_def(validate):
    @guppy.declare
    def h(q: qubit) -> None: ...

    @guppy
    def foo(q: qubit) -> None:
        h(q)
        h(q)

    @guppy
    def test(q: qubit @ owned) -> qubit:
        foo(q)
        foo(q)
        return q

    validate(test.compile_function())


def test_empty_def(validate):
    @guppy
    def test(q: qubit) -> None:
        pass

    @guppy
    def main(q: qubit @ owned) -> qubit:
        test(q)
        return q

    validate(main.compile_function())


def test_mixed_def(validate):
    @guppy.declare
    def foo(q: qubit) -> None: ...

    @guppy
    def test(
        b: int, c: qubit, d: float, a: tuple[qubit, qubit], e: qubit @ owned
    ) -> tuple[qubit, float]:
        foo(c)
        return e, b + d

    validate(test.compile_function())


def test_move_back(validate):
    @guppy.struct
    class MyStruct:
        q: qubit

    @guppy.declare
    def use(q: qubit @ owned) -> None: ...

    @guppy
    def foo(s: MyStruct) -> None:
        use(s.q)
        s.q = qubit()

    @guppy
    def bar(s: MyStruct) -> None:
        s.q = s.q

    @guppy
    def swap(s: MyStruct, t: MyStruct) -> None:
        s.q, t.q = t.q, s.q

    @guppy
    def main(s: MyStruct @ owned, t: MyStruct @ owned) -> MyStruct:
        foo(s)
        swap(s, t)
        bar(t)
        use(t.q)
        return s

    validate(main.compile_function())


def test_move_back_branch(validate):
    @guppy.struct
    class MyStruct:
        q: qubit

    @guppy.declare
    def use(q: qubit @ owned) -> None: ...

    @guppy
    def test(
        s: MyStruct, b: bool, n: int, q1: qubit @ owned, q2: qubit @ owned
    ) -> None:
        use(s.q)
        if b:
            s.q = q1
            use(q2)
        else:
            s.q = q2
            use(q1)
        use(s.q)
        i = 0
        while True:
            if i == n:
                s.q = qubit()
                return
            i += 1

    @guppy
    def main(s: MyStruct @ owned) -> MyStruct:
        test(s, False, 5, qubit(), qubit())
        return s

    validate(main.compile_function())


def test_self(validate):
    @guppy.declare
    def foo(q: qubit) -> None: ...

    @guppy.struct
    class MyStruct:
        q: qubit

        @guppy
        def bar(self: "MyStruct", b: bool) -> None:
            foo(self.q)
            if b:
                foo(self.q)

    @guppy
    def main(s: MyStruct) -> None:
        s.bar(False)

    validate(main.compile_function())


def test_subtype(validate):
    @guppy.declare
    def foo(q: qubit) -> None: ...

    @guppy
    def main() -> qubit:
        q = qubit()
        foo(q)
        return q

    validate(main.compile_function())


def test_shadow_check(validate):
    @guppy.declare
    def foo(i: qubit) -> None: ...

    @guppy
    def main(i: qubit) -> None:
        if True:
            foo(i)

    validate(main.compile_function())


def test_self_qubit(validate):
    @guppy
    def test() -> bool:
        q0 = qubit()

        result = q0.project_z()
        q0.measure()
        qubit().discard()
        return result

    validate(test.compile_function())


def test_non_terminating(validate):
    @guppy.struct
    class MyStruct:
        q1: qubit
        q2: qubit
        x: int

    @guppy.declare
    def foo(q: qubit) -> None: ...

    @guppy.declare
    def bar(s: MyStruct) -> None: ...

    @guppy
    def test1(b: bool) -> None:
        q = qubit()
        s = MyStruct(qubit(), qubit(), 0)
        while True:
            foo(q)
            bar(s)

    @guppy
    def test2(q: qubit, s: MyStruct, b: bool) -> None:
        while True:
            foo(q)
            if b:
                bar(s)

    @guppy
    def test3(q: qubit, s: MyStruct) -> None:
        while True:
            pass

    validate(test1.compile_function())
    validate(test2.compile_function())
    validate(test3.compile_function())
