from guppylang import guppy


@guppy
def foo() -> None: ...


@guppy
def bar(x: int) -> None: ...


@guppy.overload(foo, bar)
def overloaded(): ...


@guppy
def main() -> None:
    f = overloaded


main.compile()
