from guppylang import guppy


@guppy
def foo() -> None:
    pass


@guppy
def bar() -> None:
    pass


@guppy
def main(b: bool) -> None:
    if b:
        bar = foo
    bar()


main.compile_function()
