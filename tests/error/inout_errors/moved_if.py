from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.declare
def use(q: qubit @owned) -> None: ...


@guppy
def test(q: qubit, b: bool) -> None:
    if b:
        use(q)


test.compile()
