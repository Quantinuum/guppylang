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


# Compilation already rejected this typed assignment before the checking fix.
# Use check() to test that the error is raised during checking.
main.check()
