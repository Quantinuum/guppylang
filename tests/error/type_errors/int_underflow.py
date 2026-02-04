from guppylang.decorator import guppy


@guppy
def foo() -> int:
    return -9_223_372_036_854_775_809


foo.compile()
