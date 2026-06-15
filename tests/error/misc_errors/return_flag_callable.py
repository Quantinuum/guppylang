from guppylang.decorator import guppy
from guppylang.std.builtins import owned, Fn
from guppylang.std.quantum import qubit


@guppy.declare
def foo(f: "Fn[[], qubit @owned]") -> None: ...


foo.compile()
