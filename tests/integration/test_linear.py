from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.option import Option
from guppylang.std.quantum import qubit, measure

from guppylang.std.quantum.functional import cx, t, h, project_z
from guppylang_internals.decorator import custom_type
from guppylang_internals.tys.ty import NoneType


def test_id(validate):
    @guppy
    def test(q: qubit @ owned) -> qubit:
        return q

    validate(test.compile_function())


def test_assign(validate):
    @guppy
    def test(q: qubit @ owned) -> qubit:
        r = q
        s = r
        return s

    validate(test.compile_function())


def test_linear_return_order(validate):
    # See https://github.com/quantinuum/guppy/issues/35

    @guppy
    def test(q: qubit @ owned) -> tuple[qubit, bool]:
        return project_z(q)

    validate(test.compile_function())


def test_interleave(validate):
    @guppy.declare
    def f(q1: qubit @ owned, q2: qubit @ owned) -> tuple[qubit, qubit]: ...

    @guppy.declare
    def g(q1: qubit @ owned, q2: qubit @ owned) -> tuple[qubit, qubit]: ...

    @guppy
    def test(
        a: qubit @ owned, b: qubit @ owned, c: qubit @ owned, d: qubit @ owned
    ) -> tuple[qubit, qubit, qubit, qubit]:
        a, b = f(a, b)
        c, d = f(c, d)
        b, c = g(b, c)
        return a, b, c, d

    validate(test.compile_function())


def test_linear_struct(validate):
    @guppy.struct
    class MyStruct:
        q1: qubit
        q2: qubit

    @guppy.declare
    def f(q1: qubit @ owned, q2: qubit @ owned) -> tuple[qubit, qubit]: ...

    @guppy.declare
    def g(q1: qubit @ owned, q2: qubit @ owned) -> tuple[qubit, qubit]: ...

    @guppy
    def construct(q1: qubit @ owned, q2: qubit @ owned) -> MyStruct:
        return MyStruct(q1, q2)

    @guppy
    def test(
        s: MyStruct @ owned, t: MyStruct @ owned
    ) -> tuple[qubit, qubit, qubit, qubit]:
        s.q1, s.q2 = f(s.q2, s.q1)
        t.q1, t.q2 = f(t.q1, t.q2)
        s.q2, t.q1 = g(t.q1, s.q2)
        return s.q1, s.q2, t.q1, t.q2

    validate(test.compile_function())


def test_mixed_classical_linear_struct(validate):
    @guppy.struct
    class MyStruct:
        q: qubit
        x: int
        y: float

    @guppy.declare
    def f(q: qubit @ owned) -> qubit: ...

    @guppy
    def test1(s: MyStruct @ owned) -> tuple[MyStruct, float]:
        a = s.x + s.y
        s.q = f(s.q)
        return s, a * s.x

    @guppy
    def test2(s: MyStruct @ owned) -> tuple[MyStruct, int, int, int]:
        t = s
        u = t
        u.q = f(u.q)
        return u, s.x, t.x, u.x

    validate(test1.compile_function())
    validate(test2.compile_function())


def test_drop_classical_field(validate):
    @guppy.struct
    class MyStruct:
        q: qubit
        x: int

    @guppy.declare
    def f() -> MyStruct: ...

    @guppy
    def test() -> qubit:
        return f().q

    validate(test.compile_function())


def test_if(validate):
    @guppy
    def test(b: bool) -> qubit:
        if b:
            a = qubit()
            q = h(a)
        else:
            q = qubit()
        return q

    validate(test.compile_function())


def test_if_return(validate):
    @guppy
    def test(b: bool) -> qubit:
        if b:
            q = qubit()
            return h(q)
        else:
            q = qubit()
        return q

    validate(test.compile_function())


def test_if_struct_rebuild(validate):
    @guppy.struct
    class MyStruct:
        q: qubit

    @guppy
    def test1(s: MyStruct @ owned, b: bool) -> MyStruct:
        if b:
            s = MyStruct(s.q)
        return s

    @guppy
    def test2(s: MyStruct @ owned, b: bool) -> MyStruct:
        if b:
            s.q = s.q
        return s

    validate(test1.compile_function())
    validate(test2.compile_function())


def test_struct_reassign(validate):
    @guppy.struct
    class MyStruct1:
        x: "MyStruct2"

    @guppy.struct
    class MyStruct2:
        q: qubit

    @guppy.declare
    def consume(s: MyStruct2 @ owned) -> None: ...

    @guppy
    def test(s: MyStruct2 @ owned, b: bool) -> MyStruct2:
        consume(s)
        if b:
            s = MyStruct2(qubit())
            return s
        else:
            s = MyStruct1(MyStruct2(qubit()))
        return s.x

    validate(test.compile_function())


def test_struct_reassign2(validate):
    @guppy.struct
    class MyStruct:
        q1: qubit
        q2: qubit

    @guppy.declare
    def use(q: qubit @ owned) -> None: ...

    @guppy
    def test(s: MyStruct @ owned, b: bool) -> MyStruct:
        use(s.q1)
        use(s.q2)
        if b:
            s.q1 = qubit()
        else:
            s.q1 = qubit()
        s.q2 = qubit()
        return s

    validate(test.compile_function())


def test_measure(validate):
    @guppy
    def test(q: qubit @ owned, x: int) -> int:
        b = measure(q)
        return x

    validate(test.compile_function())


def test_return_call(validate):
    @guppy.declare
    def op(q: qubit @ owned) -> qubit: ...

    @guppy
    def test(q: qubit @ owned) -> qubit:
        return op(q)

    validate(test.compile_function())


def test_while(validate):
    @guppy
    def test(q: qubit @ owned, i: int) -> qubit:
        while i > 0:
            i -= 1
            q = h(q)
        return q

    validate(test.compile_function())


def test_while_break(validate):
    @guppy
    def test(q: qubit @ owned, i: int) -> qubit:
        while i > 0:
            i -= 1
            q = h(q)
            if i < 5:
                break
        return q

    validate(test.compile_function())


def test_while_continue(validate):
    @guppy
    def test(q: qubit @ owned, i: int) -> qubit:
        while i > 0:
            i -= 1
            if i % 3 == 0:
                continue
            q = h(q)
        return q

    validate(test.compile_function())


def test_while_reset(validate):
    @guppy
    def foo(i: int) -> bool:
        b = False
        while True:
            q = qubit()
            b ^= measure(q)
            if i == 0:
                break
            i -= 1
        return b

    validate(foo.compile_function())


def test_while_move_back(validate):
    @guppy.struct
    class MyStruct:
        q: qubit

    @guppy.declare
    def use(q: qubit @ owned) -> None: ...

    @guppy
    def test(s: MyStruct @ owned) -> MyStruct:
        use(s.q)
        while True:
            s.q = qubit()
            return s

    validate(test.compile_function())


def test_for(validate):
    @guppy
    def test(qs: list[tuple[qubit, qubit]] @ owned) -> list[qubit]:
        rs: list[qubit] = []
        for q1, q2 in qs:
            q1, q2 = cx(q1, q2)
            rs.append(q1)
            rs.append(q2)
        return rs

    validate(test.compile_function())


def test_for_measure(validate):
    @guppy
    def test(qs: list[qubit] @ owned) -> bool:
        parity = False
        for q in qs:
            parity |= measure(q)
        return parity

    validate(test.compile_function())


def test_for_continue(validate):
    @guppy
    def test(qs: list[qubit] @ owned) -> int:
        x = 0
        for q in qs:
            if measure(q):
                continue
            x += 1
        return x

    validate(test.compile_function())


def test_for_nonlinear_break(validate):
    @custom_type(lambda _, ctx: NoneType().to_hugr(ctx))
    class MyIter:
        """An iterator that yields linear values but is not linear itself."""

        @guppy.declare
        def __next__(self: "MyIter") -> Option[tuple[qubit, "MyIter"]]: ...

    @custom_type(lambda _, ctx: NoneType().to_hugr(ctx))
    class MyType:
        """Type that produces the iterator above."""

        @guppy.declare
        def __iter__(self: "MyType") -> MyIter: ...

    @guppy.declare
    def measure(q: qubit @ owned) -> bool: ...

    @guppy
    def test(mt: MyType, xs: list[int]) -> None:
        # We can break, since `mt` itself is not linear
        for q in mt:
            if measure(q):
                break

    validate(test.compile_function())


def test_rus(validate):
    @guppy
    def repeat_until_success(q: qubit @ owned) -> qubit:
        while True:
            aux, q = cx(t(h(qubit())), q)
            aux, q = cx(h(aux), q)
            if measure(h(t(aux))):
                break
        return q

    validate(repeat_until_success.compile_function())


def test_list_iter_arg(validate):
    @guppy
    def owned_arg(qs: list[qubit] @ owned) -> list[qubit]:
        qs = [h(q) for q in qs]
        return qs

    validate(owned_arg.compile_function())


def test_list_iter(validate):
    @guppy
    def owned_arg() -> list[qubit]:
        qs = [qubit() for _ in [0, 1, 2]]
        qs = [h(q) for q in qs]
        return qs

    validate(owned_arg.compile_function())


def test_non_terminating(validate):
    @guppy
    def test() -> None:
        q = qubit()
        while True:
            q = h(q)

    validate(test.compile_function())
