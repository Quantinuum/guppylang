from guppylang import guppy
from guppylang.std.builtins import panic, exit, comptime
from tests.util import compile_guppy


def test_basic(validate):
    @compile_guppy
    def main() -> None:
        panic("I panicked!")
        exit("I panicked!", 1)

    validate(main)


def test_discard(validate):
    @compile_guppy
    def main() -> None:
        a = 1 + 2
        panic("I panicked!", False, a)
        exit("I exited!", 2, False, a)

    validate(main)


def test_value(validate):
    @guppy
    def foo() -> int:
        return exit("I exited!", 1)

    @guppy
    def bar() -> tuple[int, float]:
        return panic("I panicked!")

    @guppy
    def baz() -> None:
        return panic("I panicked!")

    validate(foo.compile_function())
    validate(bar.compile_function())
    validate(baz.compile_function())


def test_py_message(validate):
    @compile_guppy
    def main(x: int) -> None:
        panic(comptime("I" + "panicked" + "!"))
        exit(comptime("I" + "exited" + "!"), 0)

    validate(main)


def test_comptime_panic(validate):
    @guppy.comptime
    def main() -> None:
        panic("foo")

    validate(main.compile_function())


def test_comptime_exit(validate):
    @guppy.comptime
    def main() -> None:
        exit("foo", 1)

    validate(main.compile_function())


def test_dynamic(validate):
    @compile_guppy
    def main(b: bool, s: str, i: int) -> None:
        panic("foo" if b else "bar", b)
        exit(s, i + 1)

    validate(main)
