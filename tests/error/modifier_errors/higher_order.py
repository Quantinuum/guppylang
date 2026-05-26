from guppylang.decorator import guppy
from guppylang.std.builtins import dagger
from guppylang.std.quantum import qubit, h, discard
from collections.abc import Callable


# f would need a flag to be used in dagger context, but no way to specify that yet
@guppy(dagger=True)
def test_ho(f: Callable[[qubit], None, []], q: qubit) -> None:
    f(q)


@guppy
def test() -> None:
    q = qubit()
    with dagger:
        test_ho(h, q)
    discard(q)


test.compile()
