from guppylang.decorator import guppy
from guppylang.std.builtins import control, dagger, power
from guppylang.std.quantum import qubit
from tests.util import compile_guppy


@guppy.comptime
def foo(q: qubit) -> None:
    pass


@compile_guppy
def test(ctrl: qubit, q: qubit) -> None:
    with dagger:
        with control(ctrl):
            with power(2):
                foo(q)
