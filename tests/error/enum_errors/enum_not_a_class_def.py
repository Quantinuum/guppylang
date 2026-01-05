from guppylang.decorator import guppy


@guppy.enum
def foo(x: int) -> int:
    return x


foo.compile()
