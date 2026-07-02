from guppylang.decorator import guppy


@guppy.struct(frozen=True)
class MyType[T]:
    @guppy.declare
    def foo[T](self: "MyType[T]", x: T) -> T: ...

@guppy.comptime
def test() -> None:
    mt = MyType[int]()

test.compile()