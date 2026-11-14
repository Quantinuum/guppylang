from guppylang import guppy
from guppylang.std.builtins import Function


@guppy
def foo(c: bool) -> None: ...


@guppy
def bar(c: int) -> None: ...


@guppy.overload(foo, bar)
def overloaded(): ...


@guppy
def consume(f: Function[[bool], None]) -> None: ...


@guppy
def main() -> None:
    consume(overloaded)


main.check()
