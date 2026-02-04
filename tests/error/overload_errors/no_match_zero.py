from guppylang import guppy


@guppy
def foo(x: int) -> None: ...


@guppy
def bar(x: int, y: int) -> None: ...


@guppy.overload(foo, bar)
def overloaded(): ...


@guppy
def main() -> None:
    overloaded()


main.compile()
