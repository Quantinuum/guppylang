from guppylang.decorator import guppy


@guppy.enum
class E:
    A = {}  # noqa: RUF012


@guppy.comptime
def test() -> E:

    return E

test.compile()
