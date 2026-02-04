from guppylang import guppy

T = guppy.type_var("T")


@guppy
def foo(x: T) -> T: ...


@guppy
def bar(x: T, y: T) -> T: ...


@guppy.overload(foo, bar)
def overloaded(): ...


@guppy
def main() -> None:
    overloaded[int](42)


main.compile()
