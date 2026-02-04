from guppylang.decorator import guppy


@guppy.struct
class S:
    x: int

    @guppy
    def foo(self: "S") -> None:
        pass


@guppy.comptime
def test(x: int) -> None:
    s = S(x)
    s.foo = 0


test.compile()
