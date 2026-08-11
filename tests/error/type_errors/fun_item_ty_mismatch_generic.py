from guppylang import guppy


T = guppy.type_var("T")


@guppy.declare
def foo(x: T) -> T: ...


@guppy.declare
def bar(x: T) -> T: ...


@guppy
def main(b: bool) -> int:
    if b:
        baz = foo
    else:
        baz = bar
    return baz(42)


main.compile_function()
