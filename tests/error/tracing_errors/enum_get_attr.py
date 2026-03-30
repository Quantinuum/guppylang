from guppylang.decorator import guppy


@guppy.enum
class E:
    A = {"x": int}  # noqa: RUF012
    B = {}  # noqa: RUF012


@guppy.comptime
def test() -> None:
    e = E.A(1)
    e.x


test.compile()
