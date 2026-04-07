from guppylang.decorator import guppy
from guppylang.std.builtins import dagger, power
from guppylang.std.quantum import qubit
from tests.util import compile_guppy


@guppy.comptime(dagger=True)
def foo(q: qubit) -> None:
    pass


@compile_guppy
def test(q: qubit) -> None:
    with dagger:
        with power(2):
            foo(q)
