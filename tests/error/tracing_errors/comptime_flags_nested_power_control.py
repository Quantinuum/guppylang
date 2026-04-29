from guppylang.decorator import guppy
from guppylang.std.builtins import control, power
from guppylang.std.quantum import qubit
from tests.util import compile_guppy


@guppy.comptime(power=True)
def foo(q: qubit) -> None:
    pass


@compile_guppy
def test(ctrl: qubit, q: qubit) -> None:
    with power(2):
        with control(ctrl):
            foo(q)
