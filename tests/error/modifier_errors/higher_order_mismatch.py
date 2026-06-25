from guppylang.decorator import guppy
from guppylang.std.builtins import dagger, Function
from guppylang.std.quantum import qubit, h, discard


@guppy(daggerable=True)
def test_ho(f: Function[[qubit], None], q: qubit) -> None:
    f(q)


@guppy
def test() -> None:
    q = qubit()
    with dagger:
        test_ho(h, q)
    discard(q)


test.compile()
