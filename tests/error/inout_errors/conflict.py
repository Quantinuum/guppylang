from guppylang.decorator import guppy
from guppylang.std.builtins import owned, Fn
from guppylang.std.quantum import qubit


@guppy.declare
def foo(x: qubit) -> qubit: ...


@guppy
def test() -> Fn[[qubit @owned], qubit]:
    return foo


test.compile()
