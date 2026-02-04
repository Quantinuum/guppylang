from guppylang.decorator import guppy


@guppy
def foo(x: int) -> None:
    x[0]


foo.compile()
