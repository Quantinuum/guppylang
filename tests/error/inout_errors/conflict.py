from guppylang.decorator import guppy
from guppylang.std.builtins import owned, Function
from guppylang.std.quantum import qubit


@guppy.declare
def foo(x: qubit) -> qubit: ...


@guppy
def test() -> Function[[qubit @ owned], qubit]:
    return foo


test.compile()
