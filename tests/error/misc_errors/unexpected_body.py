from guppylang.decorator import guppy


@guppy.declare
def foo() -> int:
    return 42


foo.compile()
