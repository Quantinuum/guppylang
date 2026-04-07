from guppylang.decorator import guppy
from guppylang.std.builtins import control, dagger
from guppylang.std.quantum import qubit
from tests.util import compile_guppy


@guppy.comptime(control=True)
def foo(q: qubit) -> None:
    pass


@compile_guppy
def test(ctrl: qubit, q: qubit) -> None:
    with control(ctrl):
        with dagger:
            foo(q)
