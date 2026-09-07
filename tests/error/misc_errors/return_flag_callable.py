from guppylang.decorator import guppy
from guppylang.std.builtins import owned, Function
from guppylang.std.quantum import qubit


@guppy.declare
def foo(f: "Function[[], qubit @owned]") -> None: ...


foo.compile()
