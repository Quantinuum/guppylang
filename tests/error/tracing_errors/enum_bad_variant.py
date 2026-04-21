from guppylang.decorator import guppy


@guppy.enum
class E:
    A = {}  # noqa: RUF012
    B = {}  # noqa: RUF012


@guppy.comptime
def test() -> None:
    e = E.C()


test.compile()
