from guppylang.decorator import guppy
from guppylang.std.quantum import qubit, owned
from tests.util import compile_guppy
from guppylang.std.builtins import dagger, power


@guppy.declare(dagger=True)
def discard(q: qubit @ owned) -> None: ...


@compile_guppy
def test() -> None:
    a = qubit()
    with dagger:
        with power(3):
            discard(a)


