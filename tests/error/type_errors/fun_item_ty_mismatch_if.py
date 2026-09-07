from guppylang import guppy


@guppy.declare
def foo() -> int: ...


@guppy.declare
def bar() -> int: ...


@guppy
def main(b: bool) -> int:
    baz = foo if b else bar
    return baz()


main.compile_function()
