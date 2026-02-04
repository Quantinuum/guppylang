from guppylang.decorator import guppy


@guppy
def foo() -> int:
    return 9_223_372_036_854_775_808


foo.compile()
