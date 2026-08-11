from guppylang import guppy


@guppy.declare
def foo() -> int: ...


@guppy.declare
def bar() -> int: ...


@guppy
def main(b: bool) -> int:
    if b:
        baz = foo
    else:
        baz = bar
    return baz()


main.compile_function()
