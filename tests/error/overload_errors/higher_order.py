from guppylang import guppy
from guppylang.std.builtins import Function


@guppy
def foo() -> None: ...


@guppy
def bar(x: int) -> None: ...


@guppy.overload(foo, bar)
def overloaded(): ...


@guppy
def main() -> None:
    f: Function[[], None] = overloaded


main.compile()
