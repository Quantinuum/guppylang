from guppylang import guppy

T = guppy.type_var("T")


@guppy
def foo(x: T, y: float) -> T: ...


@guppy
def bar(x: float, y: T) -> T: ...


@guppy.overload(foo, bar)
def overloaded(): ...


@guppy
def main() -> None:
    x: int = overloaded(1.2, 3.4)


main.compile()
