from guppylang import guppy


T = guppy.type_var("T")


@guppy.declare
def foo(x: T) -> T: ...


@guppy.declare
def bar(x: T) -> T: ...


@guppy
def main(b: bool) -> int:
    baz = foo if b else bar
    return baz(42)


main.compile_function()
