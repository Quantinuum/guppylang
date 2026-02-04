from guppylang.decorator import guppy


@guppy.comptime
def foo() -> None:
    pass


foo.compile()

foo()
