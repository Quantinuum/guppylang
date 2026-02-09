from guppylang import guppy, qubit
from guppylang.std.builtins import panic, exit, comptime
from tests.util import compile_guppy

from hugr.ops import Const
from hugr.std.int import IntVal


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


def test_panic_with_signal(validate):
    @compile_guppy
    def main(s: int) -> None:
        q = qubit()
        panic("I panicked with signal!", 42, q)

    validate(main)
    # The only integer constant in the HUGR should be the given signal (if the panic
    # checker didn't use it, the default would be 1 instead).
    assert any(
        isinstance(node[1].op, Const)
        and isinstance(node[1].op.val, IntVal)
        and node[1].op.val.v == 42
        for node in main.modules[0].nodes()
    )


def test_panic_with_dynamic_signal(validate):
    @compile_guppy
    def main(s: int) -> None:
        panic("I panicked with dynamic signal!", s)

    validate(main)
    # With a dynamic signal there should be no integer constants at all in the HUGR.
    assert not any(
        isinstance(node[1].op, Const) and isinstance(node[1].op.val, IntVal)
        for node in main.modules[0].nodes()
    )
