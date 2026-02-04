from collections.abc import Callable

from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.declare
def foo(x: qubit) -> qubit: ...


@guppy
def test() -> Callable[[qubit @owned], qubit]:
    return foo


test.compile()
