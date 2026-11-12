from guppylang import guppy


@guppy
def foo(c: bool) -> None: ...


@guppy
def bar(c: int) -> None: ...


@guppy.overload(foo, bar)
def overloaded(): ...


@guppy
def main() -> None:
    f = overloaded


main.check()
