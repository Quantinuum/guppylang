from guppylang.decorator import guppy


@guppy.enum
class E:
    A = {}  # noqa: RUF012

    @guppy
    def foo(self: "E") -> None:
        pass


@guppy.comptime
def test() -> None:
    e = E.A()
    e.foo = 0


test.compile()
