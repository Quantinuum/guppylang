from guppylang import guppy


@guppy
def foo(x: int) -> None: ...


@guppy
def bar(x: int, y: int) -> int: ...


@guppy.overload(foo, bar)
def overloaded(): ...


@guppy
def main() -> None:
    x: int = overloaded(42)


main.compile()
