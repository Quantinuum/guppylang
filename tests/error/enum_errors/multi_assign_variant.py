from guppylang.decorator import guppy


@guppy.enum
class MyEnum:
    A = B = {}  # noqa: RUF012


MyEnum.compile()
