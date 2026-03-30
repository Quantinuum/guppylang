from guppylang.decorator import guppy


@guppy.enum
class E:
    A = {}  # noqa: RUF012

    @guppy
    def foo(self: "E") -> None:
        pass


@guppy.comptime
def test() -> None:
    E.foo()


test.compile()
