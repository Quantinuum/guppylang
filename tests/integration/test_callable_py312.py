from guppylang.std.quantum import discard_array
from guppylang import array, qubit
from guppylang.std.builtins import Daggerable, nat
from collections.abc import Callable

from guppylang.decorator import guppy
from guppylang.std.lang import Copy, Drop


def test_struct(validate):
    @guppy.struct
    class MyStruct[F: (Callable[[int], int], Copy, Drop)]:
        f: F

        @guppy
        def call(self) -> int:
            return self.f(42)

    @guppy.declare
    def foo(x: int) -> int: ...

    @guppy.declare
    def bar[T](x: T) -> int: ...

    @guppy.declare
    def baz[T](x: int) -> T: ...

    @guppy
    def main() -> int:
        return MyStruct(foo).call() + MyStruct(bar).call() + MyStruct(baz).call()

    validate(main.compile_function())


def test_struct_generic(validate):
    @guppy.struct
    class MyStruct[S, T, F: (Callable[[S], T], Copy, Drop)]:
        f: F
        x: S

        @guppy
        def call(self) -> T:
            return self.f(self.x)

    @guppy.declare
    def foo(x: int) -> int: ...

    @guppy.declare
    def bar[U](x: U) -> int: ...

    @guppy
    def main() -> int:
        return MyStruct(foo, 42).call() + MyStruct(bar[bool], False).call()

    validate(main.compile_function())


def test_higher_order(validate):
    @guppy
    def higher_order[n: nat](
        qs: array[qubit, n], func: Callable[[array[qubit, n]], None]
    ) -> None:
        pass

    @guppy
    def generic[n: nat](qs: array[qubit, n]) -> None:
        pass

    @guppy
    def main() -> None:
        qs = array(qubit() for _ in range(3))
        higher_order(qs, generic[3])
        discard_array(qs)

    validate(main.compile())


def test_higher_order_daggerable(validate):
    @guppy
    def higher_order[n: nat](
        qs: array[qubit, n], func: Daggerable[[array[qubit, n]], None]
    ) -> None:
        pass

    @guppy(unitary=True)
    def generic(qs: array[qubit, 3]) -> None:
        pass

    @guppy
    def main() -> None:
        qs = array(qubit() for _ in range(3))
        higher_order(qs, generic)
        discard_array(qs)

    validate(main.compile())


def test_dunder_generic_struct(validate):
    @guppy.struct(frozen=True)
    class Constant[T: (Copy, Drop)]:
        value: T

        @guppy
        def __call__(self) -> T:
            return self.value

    @guppy
    def apply[T](f: Callable[[], T]) -> T:
        return f()

    @guppy
    def main() -> int:
        return apply(Constant(42)) if apply(Constant(True)) else 0

    validate(main.compile())


def test_dunder_infer_cross(validate):
    @guppy.struct(frozen=True)
    class S:
        x: int

        @guppy
        def __call__[T: Drop](self, x: T) -> int:
            return self.x

    @guppy
    def foo[T](f: Callable[[float], T]) -> T:
        return f(1.5)

    @guppy
    def main() -> int:
        return foo(S(1)) + foo(S(2))

    validate(main.compile())


def test_dunder_explicit_protocol_bound(validate):
    @guppy.struct(frozen=True)
    class Add:
        offset: int

        @guppy
        def __call__(self, x: int) -> int:
            return self.offset + x

    @guppy.struct
    class Wrapper[F: (Callable[[int], int], Copy, Drop)]:
        f: F

        @guppy
        def call(self) -> int:
            return self.f(2)

    @guppy
    def main() -> int:
        return Wrapper(Add(40)).call()

    validate(main.compile())
