from guppylang.decorator import guppy


@guppy.enum
class MyEnum:
    A, A = {}, {}  # noqa: RUF012


MyEnum.compile()
  