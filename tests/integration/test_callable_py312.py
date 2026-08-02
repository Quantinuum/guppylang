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
    from guppylang.std.builtins import array, nat
    from guppylang.std.quantum import qubit, discard_array

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

    main.compile()
