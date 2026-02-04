from guppylang.decorator import guppy

@guppy
def foo(x: bool) -> bool:
    return x


foo.compile()