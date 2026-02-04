from guppylang.decorator import guppy
from guppylang.std.quantum import qubit, h, discard
from collections.abc import Callable


# The flag is required to be used in dagger context
@guppy(dagger=True)
def test_ho(f: Callable[[qubit], None], q: qubit) -> None:
    # There is no way to use specify flags for f
    f(q)


@guppy
def test() -> None:
    q = qubit()
    with dagger:
        test_ho(h, q)
    discard(q)


test.compile()
