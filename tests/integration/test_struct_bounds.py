"""Tests for validating structs against protocols at definition time"""

from guppylang.decorator import guppy
from guppylang.std.builtins import nat, owned, array


def test_struct_bound(validate):
    """Structs can take protocol bounds."""

    @guppy.protocol
    class Foo:
        @guppy.require
        def foo(self) -> nat: ...

    @guppy.struct
    class Bar(Foo):
        @guppy
        def foo(self) -> nat:
            return 0

    @guppy
    def main() -> nat:
        x = Bar()
        return x.foo()

    validate(main.compile_function())


def test_multiple_bounds(validate):
    """Structs can take multiple protocol bounds."""

    @guppy.protocol
    class Foo:
        @guppy.require
        def foo(self) -> nat: ...

    @guppy.protocol
    class Oof:
        @guppy.require
        def foo(self) -> nat: ...

    @guppy.struct
    class Bar(Foo, Oof):
        @guppy
        def foo(self) -> nat:
            return 0

    @guppy
    def main() -> nat:
        x = Bar()
        return x.foo()

    validate(main.compile_function())


def test_proto_with_param(validate):
    """Protocol bounds can have parameters."""

    @guppy.protocol
    class Foo[T]:
        @guppy.require
        def foo(self) -> T: ...

    @guppy.struct
    class Bar(Foo[nat]):
        @guppy
        def foo(self) -> nat:
            return 0

    @guppy
    def main() -> nat:
        x = Bar()
        return x.foo()

    validate(main.compile_function())


def test_struct_with_param(validate):
    """Protocol bounds' parameters can depend on the struct's parameters."""

    @guppy.protocol
    class Foo[T]:
        @guppy.require
        def foo(self, x: T @ owned) -> T: ...

    @guppy.struct
    class Bar[T](Foo[T]):
        @guppy
        def foo(self, x: T @ owned) -> T:
            return x

    @guppy
    def main() -> nat:
        x = Bar[nat]()
        return x.foo(0)

    validate(main.compile_function())


def test_struct_with_param_fun(validate):
    """Protocol bounds' parameters can depend on the struct's parameters.

    Same as above but the dependency is more complex.
    """

    @guppy.protocol
    class Foo[T]:
        @guppy.require
        def foo(self, x: T @ owned) -> T: ...

    @guppy.struct
    class Bar[T](Foo[array[T, 2]]):
        @guppy
        def foo(self, x: array[T, 2] @ owned) -> array[T, 2]:
            return x

    @guppy
    def main() -> nat:
        x = Bar[nat]()
        return x.foo(array(1, 2))[0]

    validate(main.compile_function())


# def test_recursive_bound(validate):
#     @guppy.protocol
#     class Foo[T]:
#         @guppy.require
#         def foo(self) -> T: ...

#     @guppy.struct
#     class Bar(Foo[Bar]):
#         @guppy
#         def foo(self) -> Bar:
#             return self

#     @guppy
#     def main() -> nat:
#         x = Bar()
#         return x.foo()

#     validate(main.compile_function())


def test_instantiate_method(validate):
    """Methods validate a protocol if they have a more general type than required."""

    @guppy.protocol
    class Foo:
        @guppy.require
        def foo(self, y: nat) -> nat: ...

    @guppy.struct
    class Bar(Foo):
        @guppy
        def foo[T](self, x: T @ owned) -> T:
            return x

    @guppy
    def main() -> nat:
        x = Bar()
        return x.foo[nat](0)

    validate(main.compile_function())


# def test_universal_bound(validate):
#     @guppy.protocol
#     class Foo[T]:
#         @guppy.require
#         def foo(self, x:T @ owned) -> T: ...

#     @guppy.struct
#     class Bar(Foo[T]):
#         @guppy
#         def foo[U](self, x:U @ owned) -> U:
#             return x

#     @guppy
#     def main() -> nat:
#         x = Bar()
#         return x.foo[nat](0)

#     validate(main.compile_function())

# def test_callable(validate):
#     @guppy.struct
#     class Bar(Callable[[], nat]):
#         @guppy
#         def __call__(self) -> nat:
#             return 0

#     @guppy
#     def main() -> nat:
#         x = Bar()
#         return x(x)

#     validate(main.compile_function())
